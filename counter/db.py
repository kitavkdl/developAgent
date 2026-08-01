"""DB 접근 레이어 (Neon PostgreSQL + pgvector — DECISIONS D-06).

파이프라인 코드는 이 모듈의 함수만 호출한다. SQL이 UI 코드에 새지 않게 하는 것이
BUILD_PLAN §1의 내부 계약(테스트 가능성) 유지 방법이다.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras

from .settings import Settings

psycopg2.extras.register_uuid()


def normalized_hash(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.strip().lower().encode("utf-8")).hexdigest()


def _vec(v: list[float] | None) -> str | None:
    return "[" + ",".join(f"{x:.8f}" for x in v) + "]" if v is not None else None


class Db:
    def __init__(self, settings: Settings):
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL이 설정되지 않았습니다 (.streamlit/secrets.toml 참조)")
        self._dsn = settings.database_url
        self._conn = None

    def _connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self._dsn)
            self._conn.autocommit = True
        return self._conn

    @contextmanager
    def cursor(self):
        conn = self._connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur

    # ---- 마이그레이션 ----

    def migrate(self, sql_files: list[str]) -> None:
        for path in sql_files:
            with open(path, encoding="utf-8") as f:
                sql = f.read()
            with self.cursor() as cur:
                cur.execute(sql)

    # ---- trace_event (이벤트 스트림, 대회 규칙 3) ----

    def insert_trace_event(self, job_id, seq: int, event_type: str,
                           provider: str | None, payload: dict) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO trace_event (job_id, seq, event_type, provider, payload) "
                "VALUES (%s, %s, %s, %s, %s)",
                (job_id, seq, event_type, provider, json.dumps(payload, ensure_ascii=False, default=str)),
            )

    def fetch_trace_events(self, job_id, after_seq: int = 0) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT seq, event_type, provider, payload, created_at "
                "FROM trace_event WHERE job_id = %s AND seq > %s ORDER BY seq",
                (job_id, after_seq),
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

    # ---- 참조 데이터 ----

    def get_claim_type(self, code: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM claim_type WHERE code = %s", (code,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_falsifier_spec(self, claim_type_code: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM falsifier_spec WHERE claim_type_code = %s", (claim_type_code,))
            r = cur.fetchone()
            return dict(r) if r else None

    # ---- 업종 카테고리 (S2b) ----

    def nearest_categories(self, embedding: list[float], k: int = 5) -> list[dict]:
        """centroid가 있는 카테고리 중 코사인 유사도 상위 k. (pgvector <=> 는 cosine distance)"""
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, code, label_ko, created_by, "
                "       1 - (centroid_embedding <=> %s::vector) AS similarity "
                "FROM industry_category WHERE centroid_embedding IS NOT NULL "
                "ORDER BY centroid_embedding <=> %s::vector LIMIT %s",
                (_vec(embedding), _vec(embedding), k),
            )
            return [dict(r) for r in cur.fetchall()]

    def create_category(self, code: str, label_ko: str, embedding: list[float]) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO industry_category (code, label_ko, centroid_embedding, created_by) "
                "VALUES (%s, %s, %s::vector, 'agent_generated') "
                "ON CONFLICT (code) DO UPDATE SET label_ko = EXCLUDED.label_ko "
                "RETURNING id, code, label_ko, created_by",
                (code, label_ko, _vec(embedding)),
            )
            return dict(cur.fetchone())

    def get_default_category(self) -> dict:
        """분류 실패 시 폴백 (ARCHITECTURE §7) — 검증 파이프라인은 계속 진행돼야 함."""
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO industry_category (code, label_ko, created_by) "
                "VALUES ('uncategorized', '미분류', 'seed') "
                "ON CONFLICT (code) DO UPDATE SET label_ko = industry_category.label_ko "
                "RETURNING id, code, label_ko, created_by"
            )
            return dict(cur.fetchone())

    def set_category_centroid(self, category_id: int, embedding: list[float]) -> None:
        with self.cursor() as cur:
            cur.execute(
                "UPDATE industry_category SET centroid_embedding = %s::vector WHERE id = %s",
                (_vec(embedding), category_id),
            )

    # ---- canonical 캐시 (S3) — 매칭은 같은 업종 파티션 안에서만 (D-08) ----

    def find_canonical_by_hash(self, category_id: int, nhash: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM claim_canonical "
                "WHERE industry_category_id = %s AND normalized_hash = %s",
                (category_id, nhash),
            )
            r = cur.fetchone()
            return dict(r) if r else None

    def find_canonical_by_vector(self, category_id: int, embedding: list[float],
                                 threshold: float) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                "SELECT *, 1 - (embedding <=> %s::vector) AS similarity "
                "FROM claim_canonical "
                "WHERE industry_category_id = %s AND embedding IS NOT NULL "
                "ORDER BY embedding <=> %s::vector LIMIT 1",
                (_vec(embedding), category_id, _vec(embedding)),
            )
            r = cur.fetchone()
            if r and float(r["similarity"]) >= threshold:
                return dict(r)
            return None

    def upsert_canonical(self, *, category_id: int, claim_type_code: str,
                         normalized_text: str, embedding: list[float] | None,
                         verdict_code: str, evidence_link: str | None,
                         evidence_date, explanation: str | None,
                         executed_queries: list, ttl_days: int) -> int:
        nhash = normalized_hash(normalized_text)
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO claim_canonical (industry_category_id, claim_type_code, "
                "  normalized_text, normalized_hash, embedding, verdict_code, evidence_link, "
                "  evidence_date, explanation, executed_queries, ttl_days) "
                "VALUES (%s, %s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (industry_category_id, normalized_hash) DO UPDATE SET "
                "  verdict_code = EXCLUDED.verdict_code, evidence_link = EXCLUDED.evidence_link, "
                "  evidence_date = EXCLUDED.evidence_date, explanation = EXCLUDED.explanation, "
                "  executed_queries = EXCLUDED.executed_queries, verified_at = now(), "
                "  needs_reverification = false, dispute_count = 0 "
                "RETURNING id",
                (category_id, claim_type_code, normalized_text, nhash, _vec(embedding),
                 verdict_code, evidence_link, evidence_date, explanation,
                 json.dumps(executed_queries, ensure_ascii=False), ttl_days),
            )
            return cur.fetchone()["id"]

    def bump_canonical_reuse(self, canonical_id: int) -> None:
        with self.cursor() as cur:
            cur.execute(
                "UPDATE claim_canonical SET reuse_count = reuse_count + 1 WHERE id = %s",
                (canonical_id,),
            )

    # ---- verdict / candidate / feedback / search_log ----

    def insert_verdict(self, row: dict[str, Any]) -> str:
        cols = ", ".join(row.keys())
        ph = ", ".join(["%s"] * len(row))
        with self.cursor() as cur:
            cur.execute(
                f"INSERT INTO verdict ({cols}) VALUES ({ph}) RETURNING id",
                tuple(row.values()),
            )
            return str(cur.fetchone()["id"])

    def insert_candidate(self, *, job_id, claim_text: str, url: str, title: str | None,
                         snippet: str | None, published_date, applicability: dict,
                         passed_gate: bool) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO evidence_candidate (job_id, claim_text, url, title, snippet, "
                "  published_date, applicability, passed_gate) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (job_id, claim_text, url, title, snippet, published_date,
                 json.dumps(applicability, ensure_ascii=False), passed_gate),
            )

    def insert_feedback(self, verdict_id: str, reaction: str, note: str | None) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (verdict_id, reaction, note) VALUES (%s, %s, %s)",
                (verdict_id, reaction, note),
            )

    def fetch_verdicts(self, job_id) -> list[dict]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM verdict WHERE job_id = %s ORDER BY created_at", (job_id,))
            return [dict(r) for r in cur.fetchall()]

    def get_verdict(self, verdict_id: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM verdict WHERE id = %s", (verdict_id,))
            r = cur.fetchone()
            return dict(r) if r else None

    def apply_dispute_policy(self, canonical_id: int, count_threshold: int,
                            ratio_threshold: float) -> bool:
        """dispute가 (건수 AND 비율) 임계를 넘으면 needs_reverification=true (D-11).
        다음 조회 때 S3가 풀 재검색으로 보낸다. 반환값: 재검증 플래그 세팅 여부."""
        with self.cursor() as cur:
            cur.execute(
                "UPDATE claim_canonical SET needs_reverification = true "
                "WHERE id = %s AND dispute_count >= %s "
                "  AND dispute_count::float / GREATEST(agree_count + dispute_count, 1) >= %s "
                "RETURNING id",
                (canonical_id, count_threshold, ratio_threshold),
            )
            return cur.fetchone() is not None

    def bump_canonical_feedback(self, canonical_id: int, reaction: str) -> None:
        col = "agree_count" if reaction == "AGREE" else "dispute_count"
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE claim_canonical SET {col} = {col} + 1 WHERE id = %s",
                (canonical_id,),
            )

    def insert_search_log(self, *, job_id, provider: str, mode: str, query_text: str,
                          request_id: str | None, result_count: int | None, status: str) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO search_log (job_id, provider, mode, query_text, request_id, "
                "  result_count, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (job_id, provider, mode, query_text, request_id, result_count, status),
            )

    # ---- KPI (BUILD_PLAN §1.3) ----

    def kpi_summary(self) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT "
                " (SELECT count(*) FROM verdict) AS total_verdicts, "
                " (SELECT count(*) FROM verdict WHERE verdict_code = 'REFUTED') AS refuted, "
                " (SELECT count(*) FROM verdict WHERE verdict_code = 'PUFFERY') AS puffery, "
                " (SELECT count(*) FROM verdict WHERE cache_decision = 'HIT') AS cache_hits, "
                " (SELECT count(*) FROM evidence_candidate) AS candidates, "
                " (SELECT count(*) FROM evidence_candidate WHERE passed_gate) AS candidates_passed, "
                " (SELECT count(*) FROM claim_canonical) AS canonicals, "
                " (SELECT coalesce(sum(reuse_count), 0) FROM claim_canonical) AS total_reuse, "
                " (SELECT count(*) FROM industry_category WHERE created_by = 'agent_generated') AS agent_categories, "
                " (SELECT count(*) FROM search_log) AS searches"
            )
            return dict(cur.fetchone())

    def verdict_breakdown(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT verdict_code, count(*) AS n FROM verdict GROUP BY verdict_code ORDER BY n DESC"
            )
            return [dict(r) for r in cur.fetchall()]
