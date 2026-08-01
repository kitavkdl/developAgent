"""T9 — verdict_code != REFUTED 인데 evidence_link 있음 → DB가 거부.

실제 PostgreSQL이 필요하므로 TEST_DATABASE_URL이 설정된 경우에만 실행
(마이그레이션이 적용된 DB를 가리켜야 함). 로컬 기본 실행에서는 skip.
Fake 레벨 검증은 tests/fakes.py의 insert_verdict/upsert_canonical이 상시 수행.
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL 미설정 — 실DB 제약 테스트 skip",
)


def test_chk_evidence_only_if_refuted():
    import psycopg2

    from counter.db import Db
    from counter.settings import Settings

    db = Db(Settings(database_url=os.environ["TEST_DATABASE_URL"]))
    row = {
        "job_id": uuid.uuid4(), "claim_text": "t", "normalized_text": "t",
        "claim_category": "FALSIFIABLE", "claim_type_code": "RANKING",
        "industry_category_id": None, "route": "GENERAL",
        "verdict_code": "NOT_REFUTED",
        "evidence_link": "https://should-be-rejected.example.com",
        "evidence_date": None, "evidence_quote": None, "explanation": "x",
        "executed_queries": "[]", "cache_decision": "MISS",
        "canonical_id": None, "degraded_reason": None,
    }
    with pytest.raises(psycopg2.errors.CheckViolation):
        db.insert_verdict(row)
