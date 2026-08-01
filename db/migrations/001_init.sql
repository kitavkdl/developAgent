-- COUNTER 스키마 (DB_SCHEMA.md 부재로 PRD/ARCHITECTURE/BUILD_PLAN/DECISIONS의 인용으로부터 재구성)
-- 원칙:
--  * job 상태 테이블은 만들지 않는다 — 상태는 trace_event에서 유도 (BUILD_PLAN §1.1)
--  * claim_type은 고정 vocabulary (PRD N5) — 시드로만 채우고 앱은 절대 INSERT하지 않음
--  * industry_category는 동적 — 에이전트가 즉석 생성 가능 (DECISIONS D-07)
--  * chk_evidence_only_if_refuted: REFUTED가 아니면 evidence_link는 DB 레벨에서 거부 (T9)

CREATE EXTENSION IF NOT EXISTS vector;

-- 4값 판정 계약 (PRD §2)
CREATE TABLE IF NOT EXISTS verdict_type (
    code        TEXT PRIMARY KEY,
    label_ko    TEXT NOT NULL,
    description TEXT NOT NULL
);

-- 고정 vocabulary. REFUTED 기준(falsifier_spec)과 연결되므로 동적 생성 금지 (PRD N5)
CREATE TABLE IF NOT EXISTS claim_type (
    code                  TEXT PRIMARY KEY,
    label_ko              TEXT NOT NULL,
    -- 검색 예산: 쿼리 개수 상한 (ARCHITECTURE §3 — 하드코딩 금지, 여기서 읽음)
    default_search_budget INT  NOT NULL,
    -- NOT_REFUTED 경로 비용 상한: 쿼리당 평가 대상 문서 수 (DECISIONS D-13)
    max_evidence_per_query INT NOT NULL,
    -- 캐시 TTL (일). 유형별 14~180, 미검증 운영 기본값 (DECISIONS D-11)
    default_ttl_days      INT  NOT NULL
);

-- claim_type별 "무엇이 반례로 인정되는가" — REFUTED 게이트의 기준 (PRD N1)
CREATE TABLE IF NOT EXISTS falsifier_spec (
    id                    SERIAL PRIMARY KEY,
    claim_type_code       TEXT NOT NULL UNIQUE REFERENCES claim_type(code),
    -- {"scope_match": bool, "metric_match": bool, "timeframe_match": bool, "target_match": bool}
    -- true인 필드가 전부 충족되어야만 코드가 REFUTED를 조립한다
    required_match_fields JSONB NOT NULL,
    prompt_version        TEXT  NOT NULL
);

-- 업종 카테고리 — 동적 생성 허용. canonical 매칭의 파티션 키 (DECISIONS D-07, D-08)
CREATE TABLE IF NOT EXISTS industry_category (
    id                 SERIAL PRIMARY KEY,
    code               TEXT NOT NULL UNIQUE,
    label_ko           TEXT NOT NULL,
    centroid_embedding vector(1536),
    created_by         TEXT NOT NULL DEFAULT 'seed',  -- 'seed' | 'agent_generated'
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 검증 완료 클레임의 canonical 원장 — 캐시/델타 서치의 기반 (PRD §6-3)
CREATE TABLE IF NOT EXISTS claim_canonical (
    id                   SERIAL PRIMARY KEY,
    industry_category_id INT  NOT NULL REFERENCES industry_category(id),
    claim_type_code      TEXT NOT NULL REFERENCES claim_type(code),
    normalized_text      TEXT NOT NULL,
    normalized_hash      TEXT NOT NULL,
    embedding            vector(1536),
    verdict_code         TEXT NOT NULL REFERENCES verdict_type(code),
    evidence_link        TEXT,
    evidence_date        DATE,
    explanation          TEXT,
    executed_queries     JSONB NOT NULL DEFAULT '[]',
    ttl_days             INT  NOT NULL,
    verified_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    reuse_count          INT  NOT NULL DEFAULT 0,
    agree_count          INT  NOT NULL DEFAULT 0,
    dispute_count        INT  NOT NULL DEFAULT 0,
    needs_reverification BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT chk_evidence_only_if_refuted
        CHECK (verdict_code = 'REFUTED' OR evidence_link IS NULL),
    -- 매칭은 같은 업종 파티션 안에서만 (D-08) — 해시 유니크도 파티션 단위
    CONSTRAINT uq_canonical_partition_hash UNIQUE (industry_category_id, normalized_hash)
);
CREATE INDEX IF NOT EXISTS idx_canonical_partition ON claim_canonical (industry_category_id);

-- 최종 판정 기록 (사용자에게 나간 응답의 원본)
CREATE TABLE IF NOT EXISTS verdict (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id               UUID NOT NULL,
    claim_text           TEXT NOT NULL,
    normalized_text      TEXT NOT NULL,
    claim_category       TEXT NOT NULL,  -- FALSIFIABLE | PUFFERY | NOT_A_CLAIM
    claim_type_code      TEXT REFERENCES claim_type(code),
    industry_category_id INT  REFERENCES industry_category(id),
    route                TEXT,           -- SCIENTIFIC | GENERAL | NULL(검색 미실행)
    verdict_code         TEXT NOT NULL REFERENCES verdict_type(code),
    evidence_link        TEXT,
    evidence_date        DATE,
    evidence_quote       TEXT,
    explanation          TEXT NOT NULL,
    executed_queries     JSONB NOT NULL DEFAULT '[]',
    cache_decision       TEXT,           -- HIT | MISS | DELTA | REVERIFY | SKIP(검색 미실행)
    canonical_id         INT REFERENCES claim_canonical(id),
    degraded_reason      TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- T9: verdict_code != REFUTED 인데 evidence_link 있음 → DB가 거부
    CONSTRAINT chk_evidence_only_if_refuted
        CHECK (verdict_code = 'REFUTED' OR evidence_link IS NULL)
);
CREATE INDEX IF NOT EXISTS idx_verdict_job ON verdict (job_id);

-- S5에서 평가된 반례 후보. "후보는 많은데 REFUTED는 적다" KPI의 원천 (BUILD_PLAN §1.3)
CREATE TABLE IF NOT EXISTS evidence_candidate (
    id             SERIAL PRIMARY KEY,
    job_id         UUID NOT NULL,
    claim_text     TEXT NOT NULL,
    url            TEXT NOT NULL,
    title          TEXT,
    snippet        TEXT,
    published_date DATE,
    applicability  JSONB NOT NULL,  -- {scope_match, metric_match, timeframe_match, target_match, ...}
    passed_gate    BOOLEAN NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 판정 이후 비동기 피드백 (PRD N2 — 응답을 절대 블로킹하지 않음)
CREATE TABLE IF NOT EXISTS feedback (
    id         SERIAL PRIMARY KEY,
    verdict_id UUID NOT NULL REFERENCES verdict(id),
    reaction   TEXT NOT NULL CHECK (reaction IN ('AGREE', 'DISPUTE')),
    note       TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LINER 호출 감사 로그 (request_id 포함 — MODELS_AND_APIS §3.3)
CREATE TABLE IF NOT EXISTS search_log (
    id           SERIAL PRIMARY KEY,
    job_id       UUID NOT NULL,
    provider     TEXT NOT NULL,
    mode         TEXT NOT NULL,   -- web | scholar
    query_text   TEXT NOT NULL,
    request_id   TEXT,
    result_count INT,
    status       TEXT NOT NULL,   -- ok | timeout | rate_limited | error
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 이벤트 스트림 (대회 규칙 3). 별도 SSE 서버 없이 이 테이블을 폴링 (D-14)
CREATE TABLE IF NOT EXISTS trace_event (
    id         BIGSERIAL PRIMARY KEY,
    job_id     UUID NOT NULL,
    seq        INT  NOT NULL,     -- job 내 단조 증가, 종료 이벤트 정확히 1회
    event_type TEXT NOT NULL,
    provider   TEXT,              -- liner | openai | app — 세컨드 화면에서 색 구분
    payload    JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_trace_event_job_seq UNIQUE (job_id, seq)
);
-- 폴링 쿼리(WHERE job_id=%s AND seq>%s ORDER BY seq)가 반복 실행되므로 필수 (BUILD_PLAN §1.2)
CREATE INDEX IF NOT EXISTS idx_trace_event_job_seq ON trace_event (job_id, seq);
