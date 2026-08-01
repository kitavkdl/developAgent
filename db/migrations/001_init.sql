-- COUNTER 스키마 — DB_SCHEMA.md §1 DDL 그대로 (멱등 적용을 위해 IF NOT EXISTS만 추가).
-- 이 스키마가 지탱하는 3가지 (§0):
--  1. REFUTED 게이트 — falsifier_spec + counterexample_candidate.applicability_check
--  2. 캐시/중복탐지 — claim_canonical (업종 파티션 내에서만 매칭, D-08)
--  3. 델타 서치 — last_searched_at vs last_seen_at 구분 + search_mode
-- 원본과 다른 점 하나: claim.canonical_id FK 때문에 claim_canonical을 claim보다 먼저 생성.

CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────
-- 룩업 테이블
-- ─────────────────────────────────────────────

-- 업종 카테고리: 시드 + 에이전트 동적 생성
CREATE TABLE IF NOT EXISTS industry_category (
    category_id      TEXT PRIMARY KEY,              -- slug. 예: COSMETICS, DRONE_AG_SERVICE
    label            TEXT NOT NULL,                 -- 사람이 읽는 이름
    description      TEXT,
    centroid_embedding VECTOR(1536),                -- 유사도 매칭 기준
    created_by       TEXT NOT NULL DEFAULT 'seed',  -- seed | agent_generated
    member_claim_count INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_category_vec ON industry_category
    USING ivfflat (centroid_embedding vector_cosine_ops);

-- 클레임 유형: 고정 vocabulary. 절대 동적 생성하지 않음 (PRD N5)
CREATE TABLE IF NOT EXISTS claim_type (
    claim_type_code       TEXT PRIMARY KEY,
    description           TEXT,
    requires_search       BOOLEAN NOT NULL,
    default_search_budget INT NOT NULL,
    default_ttl_days      INT NOT NULL,             -- 델타 서치 트리거 기준
    max_evidence_per_query INT NOT NULL DEFAULT 3   -- S5 평가 대상 상한 (쿼리 1개당). D-13
);

-- 판정 라벨: 4값 고정
CREATE TABLE IF NOT EXISTS verdict_type (
    verdict_code TEXT PRIMARY KEY,
    description  TEXT
);

-- 반증 조건 명세: REFUTED 게이트의 근거
CREATE TABLE IF NOT EXISTS falsifier_spec (
    falsifier_spec_id     UUID PRIMARY KEY,
    claim_type_code       TEXT NOT NULL REFERENCES claim_type,
    required_match_fields JSONB NOT NULL,   -- {"scope":true,"metric":false,...}
    prompt_version        TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────
-- 실행 데이터
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS session (
    session_id TEXT PRIMARY KEY,
    source_app TEXT NOT NULL,        -- web | demo
    user_ref   TEXT,                 -- 익명 식별자. 개인정보 저장 금지
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ad (
    ad_id          TEXT PRIMARY KEY,
    session_id     TEXT REFERENCES session,
    source_type    TEXT NOT NULL,    -- IMAGE | URL | TEXT
    raw_input      TEXT,
    extracted_text TEXT,
    ocr_fallback_used BOOLEAN DEFAULT FALSE,
    brand_name     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 캐시의 핵심: 동일/유사 클레임을 하나로 묶는 대표 노드
-- (claim.canonical_id가 참조하므로 claim보다 먼저 생성)
CREATE TABLE IF NOT EXISTS claim_canonical (
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
CREATE INDEX IF NOT EXISTS idx_canonical_partition ON claim_canonical(industry_category_id, claim_hash);
CREATE INDEX IF NOT EXISTS idx_canonical_vec ON claim_canonical USING ivfflat (embedding_centroid vector_cosine_ops);

CREATE TABLE IF NOT EXISTS claim (
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
CREATE INDEX IF NOT EXISTS idx_claim_hash ON claim(claim_hash);
CREATE INDEX IF NOT EXISTS idx_claim_vec ON claim USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS search_log (
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

CREATE TABLE IF NOT EXISTS evidence (
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
CREATE TABLE IF NOT EXISTS counterexample_candidate (
    candidate_id        TEXT PRIMARY KEY,
    canonical_id        TEXT REFERENCES claim_canonical,
    evidence_id         TEXT REFERENCES evidence,
    falsifier_spec_id   UUID REFERENCES falsifier_spec,
    applicability_check JSONB NOT NULL,   -- {"scope_match":true,"metric_match":false,...}
    reasoning           TEXT,
    generated_by_agent  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS verdict (
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
-- DB가 물리적으로 근거 없는 REFUTED를 거부 (T9)
DO $$ BEGIN
    ALTER TABLE verdict ADD CONSTRAINT chk_evidence_only_if_refuted
      CHECK (verdict_code = 'REFUTED' OR evidence_link IS NULL);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 판정 이후 비동기 수집. 절대 응답을 블로킹하지 않음 (PRD N2)
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY,
    verdict_id  TEXT REFERENCES verdict,
    reaction    TEXT NOT NULL,       -- AGREE | DISPUTE
    user_note   TEXT,
    source      TEXT NOT NULL,       -- end_user | team | demo_judge
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trace_event (
    event_id   BIGSERIAL PRIMARY KEY,
    job_id     TEXT NOT NULL,
    seq        INT NOT NULL,
    event_type TEXT NOT NULL,
    provider   TEXT,                 -- liner | openai | null
    payload    JSONB NOT NULL,       -- 키/헤더는 마스킹, 나머지는 raw
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- 폴링(WHERE job_id=.. AND seq>..)이 핫패스 — 인덱스 없으면 폴링마다 풀스캔 (D-14)
CREATE INDEX IF NOT EXISTS idx_trace_event_job_seq ON trace_event(job_id, seq);
