# COUNTER — DB Schema

> 스택: **PostgreSQL + pgvector**. (SQLite+FAISS가 아닙니다 — `DECISIONS.md` D-06 참조)

---

## 0. 이 스키마가 지탱하는 3가지

1. **REFUTED 게이트** — `falsifier_spec` + `counterexample_candidate.applicability_check`
2. **캐시/중복탐지** — `claim_canonical` (업종 파티션 내에서만 매칭)
3. **델타 서치** — `last_searched_at` vs `last_seen_at` 구분 + `search_mode`

이 셋 중 하나라도 빠지면 제품 논리가 무너집니다. 스코프를 줄일 때도 여기는 건드리지 마세요.

---

## 1. DDL

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────
-- 룩업 테이블
-- ─────────────────────────────────────────────

-- 업종 카테고리: 시드 + 에이전트 동적 생성
CREATE TABLE industry_category (
    category_id      TEXT PRIMARY KEY,           -- slug. 예: COSMETICS, DRONE_AG_SERVICE
    label            TEXT NOT NULL,              -- 사람이 읽는 이름
    description      TEXT,
    centroid_embedding VECTOR(1536),             -- 유사도 매칭 기준
    created_by       TEXT NOT NULL DEFAULT 'seed',  -- seed | agent_generated
    member_claim_count INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_category_vec ON industry_category
    USING ivfflat (centroid_embedding vector_cosine_ops);

-- 클레임 유형: 고정 vocabulary. 절대 동적 생성하지 않음 (PRD N5)
CREATE TABLE claim_type (
    claim_type_code       TEXT PRIMARY KEY,
    description           TEXT,
    requires_search       BOOLEAN NOT NULL,
    default_search_budget INT NOT NULL,
    default_ttl_days      INT NOT NULL,          -- 델타 서치 트리거 기준
    max_evidence_per_query INT NOT NULL DEFAULT 3 -- S5 평가 대상 상한 (쿼리 1개당). DECISIONS.md D-13
);

INSERT INTO claim_type VALUES
 ('SUPERLATIVE_FIRST','최초/유일 주장',        TRUE, 4, 180, 3),
 ('RANKING',          '1위/순위 주장',          TRUE, 4,  30, 3),
 ('CLINICAL_COMPLETION','임상/시험 완료 주장',  TRUE, 3,  60, 3),
 ('AI_PERFORMANCE',   'AI 성능 주장',           TRUE, 4,  14, 3),
 ('GENERAL_FACTUAL',  '기타 검증가능 사실주장', TRUE, 3,  30, 3),
 ('PUFFERY',          '주관적 과장',           FALSE, 0, 999, 0);

-- 판정 라벨: 4값 고정
CREATE TABLE verdict_type (
    verdict_code TEXT PRIMARY KEY,
    description  TEXT
);
INSERT INTO verdict_type VALUES
 ('REFUTED','falsifier 기준 전부 충족하는 반례 존재'),
 ('NOT_REFUTED','실행 쿼리에서 기준 충족 반례 미발견. 참이라는 뜻 아님'),
 ('PUBLIC_SUBSTANTIATION_NOT_FOUND','공개 근거 자체가 확인되지 않음'),
 ('PUFFERY','주관적 과장. 검증 대상 아님');

-- 반증 조건 명세: REFUTED 게이트의 근거
CREATE TABLE falsifier_spec (
    falsifier_spec_id     UUID PRIMARY KEY,
    claim_type_code       TEXT NOT NULL REFERENCES claim_type,
    required_match_fields JSONB NOT NULL,   -- {"scope":true,"metric":false,...}
    prompt_version        TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**falsifier_spec 초기값 (반드시 이 값으로 시드):**

| claim_type | scope | metric | timeframe | target_entity | geography |
|---|---|---|---|---|---|
| `SUPERLATIVE_FIRST` | ✅ | ❌ | ✅ | ❌ | ❌ |
| `RANKING` | ❌ | ✅ | ✅ | ❌ | ✅ |
| `CLINICAL_COMPLETION` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `AI_PERFORMANCE` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `GENERAL_FACTUAL` | ✅ | ❌ | ✅ | ❌ | ❌ |

읽는 법:
- **최초 주장**은 같은 기능·제품 범주(scope)의 선행 사례가 실제 출시/발명 시점(timeframe)상 앞서야 깨집니다. 어느 회사인지(target)는 무관합니다.
- **1위 주장**은 같은 지표(metric)·같은 기간(timeframe)·같은 시장 정의(geography)의 비교 자료여야 깨집니다. 다른 회사도 1위라고 광고했다는 사실만으로는 안 깨집니다.
- **임상 완료 주장**은 그 제품 자체(target_entity)의 시험등록 상태와 불일치해야 깨집니다. 타사가 먼저 임상을 마쳤다는 건 반례가 아닙니다.

```sql
-- ─────────────────────────────────────────────
-- 실행 데이터
-- ─────────────────────────────────────────────

CREATE TABLE session (
    session_id TEXT PRIMARY KEY,
    source_app TEXT NOT NULL,        -- web | demo
    user_ref   TEXT,                 -- 익명 식별자. 개인정보 저장 금지
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ad (
    ad_id          TEXT PRIMARY KEY,
    session_id     TEXT REFERENCES session,
    source_type    TEXT NOT NULL,    -- IMAGE | URL | TEXT
    raw_input      TEXT,
    extracted_text TEXT,
    ocr_fallback_used BOOLEAN DEFAULT FALSE,
    brand_name     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE claim (
    claim_id            TEXT PRIMARY KEY,
    ad_id               TEXT REFERENCES ad,
    claim_text          TEXT NOT NULL,
    normalized_text     TEXT NOT NULL,
    claim_hash          TEXT NOT NULL,        -- normalized_text의 SHA-256
    embedding           VECTOR(1536),
    claim_category      TEXT NOT NULL,        -- FALSIFIABLE | PUFFERY | NOT_A_CLAIM
    claim_type_code     TEXT REFERENCES claim_type,
    verification_route  TEXT,                 -- SCIENTIFIC | GENERAL | NULL
    industry_category_id TEXT REFERENCES industry_category,
    industry_similarity  REAL,
    canonical_id        TEXT REFERENCES claim_canonical,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_claim_hash ON claim(claim_hash);
CREATE INDEX idx_claim_vec ON claim USING ivfflat (embedding vector_cosine_ops);

-- 캐시의 핵심: 동일/유사 클레임을 하나로 묶는 대표 노드
CREATE TABLE claim_canonical (
    canonical_id         TEXT PRIMARY KEY,
    representative_claim_id TEXT,
    claim_type_code      TEXT REFERENCES claim_type,
    industry_category_id TEXT NOT NULL REFERENCES industry_category,  -- 파티션 키
    claim_hash           TEXT NOT NULL,
    embedding_centroid   VECTOR(1536),
    member_count         INT NOT NULL DEFAULT 1,
    reuse_count          INT NOT NULL DEFAULT 0,   -- 캐시 히트 횟수 (KPI)
    agree_count          INT NOT NULL DEFAULT 0,
    dispute_count        INT NOT NULL DEFAULT 0,
    needs_reverification BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at         TIMESTAMPTZ NOT NULL DEFAULT now(),  -- 조회(캐시 포함) 시각
    last_searched_at     TIMESTAMPTZ,                          -- 실제 검색 실행 시각
    similarity_threshold_used REAL
);
CREATE INDEX idx_canonical_partition ON claim_canonical(industry_category_id, claim_hash);
CREATE INDEX idx_canonical_vec ON claim_canonical USING ivfflat (embedding_centroid vector_cosine_ops);
```

**`last_seen_at` vs `last_searched_at` — 헷갈리지 마세요.**
캐시로만 계속 서빙되면 `last_seen_at`은 갱신되지만 `last_searched_at`은 그대로입니다. **이 간극이 델타 서치를 트리거하는 기준**입니다.

```sql
CREATE TABLE search_log (
    log_id       TEXT PRIMARY KEY,
    canonical_id TEXT REFERENCES claim_canonical,
    claim_id     TEXT REFERENCES claim,
    provider     TEXT NOT NULL,      -- liner
    search_tool  TEXT NOT NULL,      -- liner_web | liner_scholar
    search_mode  TEXT NOT NULL,      -- full | delta
    date_from    DATE,               -- delta 모드에서만
    query_text   TEXT NOT NULL,
    hypothesis   TEXT,               -- 이 쿼리가 검증하려는 반증 가설
    language     TEXT,
    result_count INT,
    latency_ms   INT,
    status       TEXT NOT NULL,      -- success | timeout | error | empty
    provider_request_id TEXT,
    searched_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE evidence (
    evidence_id    TEXT PRIMARY KEY,
    log_id         TEXT REFERENCES search_log,
    url            TEXT NOT NULL,
    title          TEXT,
    snippet        TEXT,
    published_date DATE,             -- 없으면 NULL. 절대 추측해서 채우지 말 것
    source_domain  TEXT,
    access_level   TEXT,             -- metadata | snippet | abstract
    retrieved_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- REFUTED 게이트의 입력
CREATE TABLE counterexample_candidate (
    candidate_id        TEXT PRIMARY KEY,
    canonical_id        TEXT REFERENCES claim_canonical,
    evidence_id         TEXT REFERENCES evidence,
    falsifier_spec_id   UUID REFERENCES falsifier_spec,
    applicability_check JSONB NOT NULL,   -- {"scope_match":true,"metric_match":false,...}
    reasoning           TEXT,
    generated_by_agent  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE verdict (
    verdict_id        TEXT PRIMARY KEY,
    claim_id          TEXT REFERENCES claim,
    canonical_id      TEXT REFERENCES claim_canonical,
    verdict_code      TEXT NOT NULL REFERENCES verdict_type,
    evidence_link     TEXT,          -- REFUTED가 아니면 반드시 NULL
    evidence_date     DATE,
    search_count      INT NOT NULL,
    confidence_source TEXT NOT NULL, -- fresh_search | cached_reuse | delta_search
    required_evidence_note TEXT,
    reasoning         TEXT,
    assembled_by      TEXT NOT NULL, -- 항상 에이전트. 사람 값이 들어가면 버그
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE verdict ADD CONSTRAINT chk_evidence_only_if_refuted
  CHECK (verdict_code = 'REFUTED' OR evidence_link IS NULL);

-- 판정 이후 비동기 수집. 절대 응답을 블로킹하지 않음 (PRD N2)
CREATE TABLE feedback (
    feedback_id TEXT PRIMARY KEY,
    verdict_id  TEXT REFERENCES verdict,
    reaction    TEXT NOT NULL,       -- AGREE | DISPUTE
    user_note   TEXT,
    source      TEXT NOT NULL,       -- end_user | team | demo_judge
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE trace_event (
    event_id   BIGSERIAL PRIMARY KEY,
    job_id     TEXT NOT NULL,
    seq        INT NOT NULL,
    event_type TEXT NOT NULL,
    provider   TEXT,                 -- liner | openai | null
    payload    JSONB NOT NULL,       -- 키/헤더는 마스킹, 나머지는 raw
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_trace_event_job_seq ON trace_event(job_id, seq);
```

**`idx_trace_event_job_seq`는 Streamlit 단일 배포 결정(`DECISIONS.md` D-14) 이후 추가됨.** SSE로 서버가 이벤트를 push하던 구조에서, 세컨드 화면이 `WHERE job_id=... AND seq > ...`를 초 단위로 반복 폴링하는 구조로 바뀌면서 이 조회 패턴이 핫패스가 됐습니다. 인덱스 없이는 폴링마다 풀스캔이라 Neon 콜드스타트/지연과 겹치면 세컨드 화면이 눈에 띄게 느려질 수 있습니다.

`chk_evidence_only_if_refuted` 제약은 의도적입니다. **DB가 물리적으로 근거 없는 REFUTED를 거부**하게 만듭니다.

---

## 2. 캐시 라우팅 로직 (결정론적 — LLM 아님)

```python
def route_cache(claim) -> CacheDecision:
    # 1. 같은 업종 파티션 안에서만 탐색
    part = claim.industry_category_id

    # 2. 정확 매칭 우선
    c = find_canonical(category=part, claim_hash=claim.claim_hash)

    # 3. 없으면 같은 파티션 내 벡터 유사도
    if not c:
        cands = vector_search(claim.embedding, partition=part, k=5)
        if cands and cosine(claim.embedding, cands[0].centroid) >= CANONICAL_THRESHOLD:
            c = cands[0]

    if not c:
        return MISS                       # → 풀 검색

    c.member_count += 1
    c.last_seen_at = now()

    if c.needs_reverification:
        return REVERIFY                   # → 풀 검색 (이의제기 트리거)

    ttl = claim_type[c.claim_type_code].default_ttl_days
    if c.last_searched_at and (now() - c.last_searched_at).days <= ttl:
        c.reuse_count += 1
        return HIT                        # → 재검색 없이 즉시 응답

    return DELTA                          # → date_from=last_searched_at으로 좁힌 검색
```

`CANONICAL_THRESHOLD` 초기값 **0.85** (카테고리 임계 0.75보다 엄격 — 클레임 매칭은 더 보수적이어야 오매칭이 없습니다). 미검증 추정치입니다.

### 트리거 구분 — 절대 섞지 마세요

| 트리거 | 처리 | 이유 |
|---|---|---|
| **시간 간극(TTL 초과)** | 델타 서치 | 기존 증거는 유효하다고 가정, 간극 기간만 확인 |
| **이의제기(dispute 누적)** | 풀 재검색 | 기존 증거 자체가 틀렸을 수 있음 |

dispute가 쌓인 canonical에 델타만 돌리면, 원래 틀렸던 과거 증거 위에 새 기간만 얹는 꼴이라 오판정이 안 고쳐집니다.

### 자가교정 트리거 (완전 자동)

```python
if c.dispute_count >= 3 and c.dispute_count / (c.agree_count + c.dispute_count) >= 0.3:
    c.needs_reverification = True
```
재검색 후 새 verdict가 조립되면 `needs_reverification`을 false로 리셋합니다.

---

## 3. REFUTED 게이트 (PRD N1 — 이 코드가 유일한 정확성 방어선)

```python
def assemble_verdict(canonical, candidates, spec, search_count) -> Verdict:
    required = [f for f, req in spec.required_match_fields.items() if req]

    for cand in candidates:
        if all(cand.applicability_check.get(f + "_match") for f in required):
            return Verdict(
                verdict_code="REFUTED",
                evidence_link=cand.evidence.url,
                evidence_date=cand.evidence.published_date,
                search_count=search_count,
            )

    return Verdict(verdict_code="NOT_REFUTED", evidence_link=None,
                   search_count=search_count)
```

**금지 사항:**
- LLM에게 최종 `verdict_code`를 생성하게 하지 말 것. LLM은 `applicability_check`의 boolean만 생성합니다.
- S5의 문자열 매칭(스니펫에 범주어 포함 등)만으로 REFUTED를 확정하지 말 것. 그건 candidate 승격 기준일 뿐입니다.
- `evidence_link`에 검색 결과에 없던 URL을 넣지 말 것.

**`candidates` 목록의 크기는 어디서 정해지는가**: `assemble_verdict`에 들어오는 `candidates`는 무제한이 아니라, 쿼리 실행 단계에서 `claim_type.max_evidence_per_query`로 이미 상한이 걸린 상태로 들어옵니다 (쿼리 개수 × max_evidence_per_query가 이론상 최대치). REFUTED가 조기 확정되지 않는 `NOT_REFUTED` 경로에서는 이 목록 전체가 S5(`gpt-5.6-sol`, high effort)로 평가되므로, 이 상한이 없으면 검색 결과가 많을수록 sol 호출이 그만큼 늘어납니다. 이 상한은 애플리케이션 코드가 검색 결과를 잘라내는 지점이지, LLM이 스스로 "이 정도만 보겠다"고 판단하는 게 아닙니다.

---

## 4. 시드 데이터

**업종 카테고리 (10~15개)**: 뷰티/퍼스널케어, 가전/전자, 교육/에듀테크, 식품/건강기능식품, 금융/핀테크, 패션/의류, 반려동물, 유아동, 피트니스/웰니스, 생활화학, 디지털헬스, 여행/숙박, 부동산/인테리어

각 카테고리마다 대표 문장 3~5개를 임베딩해 평균낸 값을 `centroid_embedding`에 저장. 서비스 시작 시 1회 생성.

**⚠️ 데모 데이터는 2~3개 업종에 몰아서 시드하세요.** 파티셔닝 때문에 카테고리 간에는 캐시 히트가 절대 안 생깁니다. 여러 업종에 얇게 뿌리면 데모에서 보여줄 `reuse_count`가 왜소해 보입니다. 최상급 주장이 흔한 업종(뷰티, 건강기능식품 등) 2~3개에 집중하세요.

---

## 5. KPI 쿼리 (데모 대시보드용)

```sql
-- 캐시 히트율
SELECT SUM(reuse_count)::float / NULLIF(SUM(member_count),0) FROM claim_canonical;

-- 업종별 누적 (프론트 클러스터 시각화용)
SELECT ic.label, ic.created_by, COUNT(c.claim_id)
FROM industry_category ic LEFT JOIN claim c ON c.industry_category_id = ic.category_id
GROUP BY 1,2 ORDER BY 3 DESC;

-- 에이전트가 즉석 생성한 카테고리 (Real-time Adaptability 증거)
SELECT category_id, label, created_at FROM industry_category
WHERE created_by = 'agent_generated' ORDER BY created_at DESC;

-- 델타 서치 절감 (축적 효과의 정량 증거)
SELECT search_mode, COUNT(*), AVG(latency_ms) FROM search_log GROUP BY 1;

-- REFUTED 게이트 작동 증거 (후보 중 실제로 통과한 비율)
SELECT
  (SELECT COUNT(*) FROM verdict WHERE verdict_code='REFUTED') AS passed,
  (SELECT COUNT(*) FROM counterexample_candidate) AS candidates;
```

마지막 쿼리가 중요합니다. **후보는 많은데 REFUTED는 적다**는 게 게이트가 실제로 오판정을 걸러내고 있다는 증거입니다.
