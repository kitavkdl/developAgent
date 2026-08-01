"""DB 접근 레이어 (Neon PostgreSQL + pgvector — DECISIONS D-06, 스키마는 DB_SCHEMA.md).

파이프라인 코드는 이 모듈의 함수만 호출한다. SQL이 UI 코드에 새지 않게 하는 것이
BUILD_PLAN §1의 내부 계약(테스트 가능성) 유지 방법이다.
ID는 전부 TEXT(uuid 문자열) — DB_SCHEMA.md DDL 기준.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras


def normalized_hash(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.strip().lower().encode("utf-8")).hexdigest()


def new_id() -> str:
    return str(uuid.uuid4())


def _vec(v: list[float] | None) -> str | None:
    return "[" + ",".join(f"{x:.8f}" for x in v) + "]" if v is not None else None


class Db:
    def __init__(self, settings):
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL이 설정되지 않았습니다 (.streamlit/secrets.toml 참조)")
        self._dsn = settings.database_url
        self._conn = None

    def _connection(self):
        if self._conn is not None and not self._conn.closed:
            # Neon scale-to-zero 콜드스타트/유휴 끊김은 서버 쪽에서 조용히 커넥션을
            # 끊으므로 conn.closed로는 감지 안 됨 → 가벼운 헬스체크로 선제 확인 (M7).
            try:
                with self._conn.cursor() as probe:
                    probe.execute("SELECT 1")
                return self._conn
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                self._conn = None
        self._conn = psycopg2.connect(self._dsn)
        self._conn.autocommit = True
        return self._conn

    def close(self) -> None:
        """스레드 전용 커넥션(백그라운드 job worker) 정리용. 공유 캐시 인스턴스에는
        호출하지 말 것 — 다른 세션이 계속 쓰고 있을 수 있다."""
        if self._conn is not None and not self._conn.closed:
            self._conn.close()

    @contextmanager
    def cursor(self):
        # @contextmanager 제너레이터는 정확히 한 번만 yield해야 하므로
        # 여기서 재시도용 2차 yield를 두면 안 됨 (contextlib이
        # "generator didn't stop after throw()"로 거부함). 재연결은
        # _connection()의 선제 헬스체크가 담당하고, 여기서는 실행 중
        # 끊기는 드문 케이스에 한해 커넥션만 무효화하고 그대로 전파한다.
        conn = self._connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
        except psycopg2.OperationalError:
            self._conn = None
            raise

    # ---- 마이그레이션 ----

    def migrate(self, sql_files: list[str]) -> None:
        for path in sql_files:
            with open(path, encoding="utf-8") as f:
                sql = f.read()
            with self.cursor() as cur:
                cur.execute(sql)

    # ---- trace_event (이벤트 스트림, 대회 규칙 3) ----

    def insert_trace_event(self, job_id: str, seq: int, event_type: str,
                           provider: str | None, payload: dict) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO trace_event (job_id, seq, event_type, provider, payload) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(job_id), seq, event_type, provider,
                 json.dumps(payload, ensure_ascii=False, default=str)),
            )

    def fetch_trace_events(self, job_id: str, after_seq: int = 0) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT seq, event_type, provider, payload, created_at "
                "FROM trace_event WHERE job_id = %s AND seq > %s ORDER BY seq",
                (str(job_id), after_seq),
            )
            return [dict(r) for r in cur.fetchall()]

    def fetch_recent_jobs(self, limit: int = 20) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT job_id, MIN(created_at) AS started_at, "
                "       MAX(CASE WHEN event_type LIKE 'job.%%' AND event_type <> 'job.created' "
                "                THEN event_type END) AS terminal_event "
                "FROM trace_event GROUP BY job_id ORDER BY MIN(created_at) DESC LIMIT %s",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    # ---- session / ad ----

    def insert_session(self, source_app: str = "web") -> str:
        sid = new_id()
        with self.cursor() as cur:
            cur.execute("INSERT INTO session (session_id, source_app) VALUES (%s, %s)",
                        (sid, source_app))
        return sid

    def insert_ad(self, *, ad_id: str, session_id: str, source_type: str,
                  raw_input: str | None, extracted_text: str | None,
                  brand_name: str | None, ocr_fallback_used: bool = False) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO ad (ad_id, session_id, source_type, raw_input, extracted_text, "
                "ocr_fallback_used, brand_name) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (ad_id, session_id, source_type, raw_input, extracted_text,
                 ocr_fallback_used, brand_name),
            )

    # ---- claim ----

    def insert_claim(self, *, ad_id: str, claim_text: str, normalized_text: str,
                     embedding: list[float] | None, claim_category: str,
                     claim_type_code: str | None) -> str:
        cid = new_id()
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO claim (claim_id, ad_id, claim_text, normalized_text, claim_hash, "
                "embedding, claim_category, claim_type_code) "
                "VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s)",
                (cid, ad_id, claim_text, normalized_text, normalized_hash(normalized_text),
                 _vec(embedding), claim_category, claim_type_code),
            )
        return cid

    def update_claim_routing(self, claim_id: str, *, verification_route: str | None = None,
                             industry_category_id: str | None = None,
                             industry_similarity: float | None = None,
                             canonical_id: str | None = None) -> None:
        with self.cursor() as cur:
            cur.execute(
                "UPDATE claim SET "
                "verification_route = COALESCE(%s, verification_route), "
                "industry_category_id = COALESCE(%s, industry_category_id), "
                "industry_similarity = COALESCE(%s, industry_similarity), "
                "canonical_id = COALESCE(%s, canonical_id) WHERE claim_id = %s",
                (verification_route, industry_category_id, industry_similarity,
                 canonical_id, claim_id),
            )

    # ---- 참조 데이터 ----

    def get_claim_type(self, code: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM claim_type WHERE claim_type_code = %s", (code,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_falsifier_spec(self, claim_type_code: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM falsifier_spec WHERE claim_type_code = %s "
                "ORDER BY created_at DESC LIMIT 1",
                (claim_type_code,),
            )
            r = cur.fetchone()
            return dict(r) if r else None

    # ---- 업종 카테고리 (S2b) ----

    def nearest_categories(self, embedding: list[float], k: int = 5) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT category_id, label, created_by, "
                "       1 - (centroid_embedding <=> %s::vector) AS similarity "
                "FROM industry_category WHERE centroid_embedding IS NOT NULL "
                "ORDER BY centroid_embedding <=> %s::vector LIMIT %s",
                (_vec(embedding), _vec(embedding), k),
            )
            return [dict(r) for r in cur.fetchall()]

    def create_category(self, category_id: str, label: str,
                        embedding: list[float]) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO industry_category (category_id, label, centroid_embedding, created_by) "
                "VALUES (%s, %s, %s::vector, 'agent_generated') "
                "ON CONFLICT (category_id) DO UPDATE SET label = EXCLUDED.label "
                "RETURNING category_id, label, created_by",
                (category_id, label, _vec(embedding)),
            )
            return dict(cur.fetchone())

    def get_default_category(self) -> dict:
        """분류 실패 시 폴백 (ARCHITECTURE §7) — 검증 파이프라인은 계속 진행돼야 함."""
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO industry_category (category_id, label, created_by) "
                "VALUES ('UNCATEGORIZED', '미분류 (폴백)', 'seed') "
                "ON CONFLICT (category_id) DO UPDATE SET label = industry_category.label "
                "RETURNING category_id, label, created_by"
            )
            return dict(cur.fetchone())

    def set_category_centroid(self, category_id: str, embedding: list[float]) -> None:
        with self.cursor() as cur:
            cur.execute(
                "UPDATE industry_category SET centroid_embedding = %s::vector "
                "WHERE category_id = %s",
                (_vec(embedding), category_id),
            )

    # ---- canonical 캐시 (S3) — 매칭은 같은 업종 파티션 안에서만 (D-08) ----

    def find_canonical_by_hash(self, category_id: str, claim_hash: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM claim_canonical "
                "WHERE industry_category_id = %s AND claim_hash = %s",
                (category_id, claim_hash),
            )
            r = cur.fetchone()
            return dict(r) if r else None

    def find_canonical_by_vector(self, category_id: str, embedding: list[float],
                                 threshold: float) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                "SELECT *, 1 - (embedding_centroid <=> %s::vector) AS similarity "
                "FROM claim_canonical "
                "WHERE industry_category_id = %s AND embedding_centroid IS NOT NULL "
                "ORDER BY embedding_centroid <=> %s::vector LIMIT 1",
                (_vec(embedding), category_id, _vec(embedding)),
            )
            r = cur.fetchone()
            if r and float(r["similarity"]) >= threshold:
                return dict(r)
            return None

    def touch_canonical_seen(self, canonical_id: str) -> None:
        """매칭 시 member_count++/last_seen_at 갱신 (DB_SCHEMA.md §2 route_cache)."""
        with self.cursor() as cur:
            cur.execute(
                "UPDATE claim_canonical SET member_count = member_count + 1, "
                "last_seen_at = now() WHERE canonical_id = %s",
                (canonical_id,),
            )

    def bump_canonical_reuse(self, canonical_id: str) -> None:
        with self.cursor() as cur:
            cur.execute(
                "UPDATE claim_canonical SET reuse_count = reuse_count + 1 "
                "WHERE canonical_id = %s",
                (canonical_id,),
            )

    def create_canonical(self, *, representative_claim_id: str, claim_type_code: str,
                         industry_category_id: str, claim_hash: str,
                         embedding: list[float] | None,
                         similarity_threshold_used: float) -> str:
        cid = new_id()
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO claim_canonical (canonical_id, representative_claim_id, "
                "claim_type_code, industry_category_id, claim_hash, embedding_centroid, "
                "last_searched_at, similarity_threshold_used) "
                "VALUES (%s, %s, %s, %s, %s, %s::vector, now(), %s) "
                "RETURNING canonical_id",
                (cid, representative_claim_id, claim_type_code, industry_category_id,
                 claim_hash, _vec(embedding), similarity_threshold_used),
            )
            return cur.fetchone()["canonical_id"]

    def mark_canonical_searched(self, canonical_id: str) -> None:
        """재검색(델타/재검증) 완료 — last_searched_at 갱신 + 재검증 플래그 리셋."""
        with self.cursor() as cur:
            cur.execute(
                "UPDATE claim_canonical SET last_searched_at = now(), "
                "needs_reverification = FALSE WHERE canonical_id = %s",
                (canonical_id,),
            )

    # ---- search_log / evidence / candidate ----

    def insert_search_log(self, *, canonical_id: str | None, claim_id: str | None,
                          search_tool: str, search_mode: str, date_from,
                          query_text: str, hypothesis: str | None, language: str | None,
                          result_count: int | None, latency_ms: int | None,
                          status: str, provider_request_id: str | None) -> str:
        lid = new_id()
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO search_log (log_id, canonical_id, claim_id, provider, "
                "search_tool, search_mode, date_from, query_text, hypothesis, language, "
                "result_count, latency_ms, status, provider_request_id) "
                "VALUES (%s, %s, %s, 'liner', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (lid, canonical_id, claim_id, search_tool, search_mode, date_from,
                 query_text, hypothesis, language, result_count, latency_ms, status,
                 provider_request_id),
            )
        return lid

    def link_search_logs_to_canonical(self, claim_id: str, canonical_id: str) -> None:
        """canonical은 검색 이후에 생성되므로, 생성 직후 로그를 역으로 연결한다."""
        with self.cursor() as cur:
            cur.execute(
                "UPDATE search_log SET canonical_id = %s "
                "WHERE claim_id = %s AND canonical_id IS NULL",
                (canonical_id, claim_id),
            )

    def insert_evidence(self, *, log_id: str, url: str, title: str | None,
                        snippet: str | None, published_date, source_domain: str | None,
                        access_level: str = "snippet") -> str:
        eid = new_id()
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO evidence (evidence_id, log_id, url, title, snippet, "
                "published_date, source_domain, access_level) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (eid, log_id, url, title, snippet, published_date, source_domain,
                 access_level),
            )
        return eid

    def insert_candidate(self, *, canonical_id: str | None, evidence_id: str,
                         falsifier_spec_id, applicability_check: dict,
                         reasoning: str | None, generated_by_agent: str) -> str:
        cid = new_id()
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO counterexample_candidate (candidate_id, canonical_id, "
                "evidence_id, falsifier_spec_id, applicability_check, reasoning, "
                "generated_by_agent) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (cid, canonical_id, evidence_id, falsifier_spec_id,
                 json.dumps(applicability_check, ensure_ascii=False), reasoning,
                 generated_by_agent),
            )
        return cid

    # ---- verdict / feedback ----

    def insert_verdict(self, *, claim_id: str, canonical_id: str | None,
                       verdict_code: str, evidence_link: str | None, evidence_date,
                       search_count: int, confidence_source: str,
                       required_evidence_note: str | None, reasoning: str | None,
                       assembled_by: str = "agent") -> str:
        vid = new_id()
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO verdict (verdict_id, claim_id, canonical_id, verdict_code, "
                "evidence_link, evidence_date, search_count, confidence_source, "
                "required_evidence_note, reasoning, assembled_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (vid, claim_id, canonical_id, verdict_code, evidence_link, evidence_date,
                 search_count, confidence_source, required_evidence_note, reasoning,
                 assembled_by),
            )
        return vid

    def latest_verdict_for_canonical(self, canonical_id: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM verdict WHERE canonical_id = %s "
                "ORDER BY created_at DESC LIMIT 1",
                (canonical_id,),
            )
            r = cur.fetchone()
            return dict(r) if r else None

    def fetch_verdicts(self, job_id: str) -> list[dict]:
        """job_id == ad_id (한 job이 광고 1건을 처리). claim JOIN으로 원문 문구 포함."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT v.*, c.claim_text, c.claim_category, c.claim_type_code AS claim_type "
                "FROM verdict v JOIN claim c ON v.claim_id = c.claim_id "
                "WHERE c.ad_id = %s ORDER BY v.created_at",
                (str(job_id),),
            )
            return [dict(r) for r in cur.fetchall()]

    def fetch_executed_queries(self, claim_id: str, canonical_id: str | None) -> list[str]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT query_text FROM search_log "
                "WHERE claim_id = %s OR (%s::text IS NOT NULL AND canonical_id = %s) "
                "ORDER BY query_text",
                (claim_id, canonical_id, canonical_id),
            )
            return [r["query_text"] for r in cur.fetchall()]

    def get_verdict(self, verdict_id: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM verdict WHERE verdict_id = %s", (verdict_id,))
            r = cur.fetchone()
            return dict(r) if r else None

    def insert_feedback(self, verdict_id: str, reaction: str, note: str | None,
                        source: str = "end_user") -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (feedback_id, verdict_id, reaction, user_note, source) "
                "VALUES (%s, %s, %s, %s, %s)",
                (new_id(), verdict_id, reaction, note, source),
            )

    def bump_canonical_feedback(self, canonical_id: str, reaction: str) -> None:
        col = "agree_count" if reaction == "AGREE" else "dispute_count"
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE claim_canonical SET {col} = {col} + 1 WHERE canonical_id = %s",
                (canonical_id,),
            )

    def apply_dispute_policy(self, canonical_id: str, count_threshold: int,
                             ratio_threshold: float) -> bool:
        """자가교정 트리거 (DB_SCHEMA.md §2 — 완전 자동): dispute가 건수 AND 비율 임계를
        넘으면 needs_reverification=true → 다음 조회 때 풀 재검색(REVERIFY)."""
        with self.cursor() as cur:
            cur.execute(
                "UPDATE claim_canonical SET needs_reverification = TRUE "
                "WHERE canonical_id = %s AND dispute_count >= %s "
                "  AND dispute_count::float / GREATEST(agree_count + dispute_count, 1) >= %s "
                "RETURNING canonical_id",
                (canonical_id, count_threshold, ratio_threshold),
            )
            return cur.fetchone() is not None

    # ---- KPI (DB_SCHEMA.md §5) ----

    def kpi_summary(self) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT "
                " (SELECT count(*) FROM verdict) AS total_verdicts, "
                " (SELECT count(*) FROM verdict WHERE verdict_code = 'REFUTED') AS refuted, "
                " (SELECT count(*) FROM verdict WHERE verdict_code = 'PUFFERY') AS puffery, "
                " (SELECT count(*) FROM verdict WHERE confidence_source = 'cached_reuse') AS cache_hits, "
                " (SELECT count(*) FROM counterexample_candidate) AS candidates, "
                " (SELECT count(*) FROM claim_canonical) AS canonicals, "
                " (SELECT coalesce(sum(reuse_count), 0) FROM claim_canonical) AS total_reuse, "
                " (SELECT coalesce(sum(reuse_count)::float / NULLIF(sum(member_count), 0), 0) "
                "    FROM claim_canonical) AS cache_hit_ratio, "
                " (SELECT count(*) FROM industry_category WHERE created_by = 'agent_generated') AS agent_categories, "
                " (SELECT count(*) FROM search_log) AS searches"
            )
            return dict(cur.fetchone())

    def verdict_breakdown(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT verdict_code, count(*) AS n FROM verdict "
                "GROUP BY verdict_code ORDER BY n DESC"
            )
            return [dict(r) for r in cur.fetchall()]

    def search_mode_breakdown(self) -> list[dict]:
        """델타 서치 절감 — 축적 효과의 정량 증거 (DB_SCHEMA.md §5)."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT search_mode, COUNT(*) AS n, AVG(latency_ms) AS avg_latency_ms "
                "FROM search_log GROUP BY 1"
            )
            return [dict(r) for r in cur.fetchall()]

    def search_status_breakdown(self) -> list[dict]:
        """LINER 호출이 성공(success/empty)인지 실패(error/timeout)인지 —
        candidate=0 원인이 '검색 실패'인지 '결과 없음'인지 즉시 구분하기 위함."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT status, COUNT(*) AS n, AVG(latency_ms) AS avg_latency_ms "
                "FROM search_log GROUP BY 1 ORDER BY n DESC"
            )
            return [dict(r) for r in cur.fetchall()]

    def agent_categories(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT category_id, label, created_at FROM industry_category "
                "WHERE created_by = 'agent_generated' ORDER BY created_at DESC"
            )
            return [dict(r) for r in cur.fetchall()]
