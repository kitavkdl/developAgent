"""T9 — verdict_code NOT IN (CONTRADICTED, CORROBORATED)인데 evidence_link 있음 → DB가 거부.

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


def test_chk_evidence_only_if_contradicted_or_corroborated():
    import psycopg2

    from counter.db import Db
    from counter.settings import Settings

    db = Db(Settings(database_url=os.environ["TEST_DATABASE_URL"]))
    with pytest.raises(psycopg2.errors.CheckViolation):
        db.insert_verdict(
            claim_id=None, canonical_id=None, verdict_code="UNVERIFIED",
            evidence_link="https://should-be-rejected.example.com",
            evidence_date=None, search_count=1, confidence_source="fresh_search",
            required_evidence_note=None, reasoning=str(uuid.uuid4()),
        )
