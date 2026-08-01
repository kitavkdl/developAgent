"""검토한 근거 문서 노출 기능 회귀 테스트.

CONTRADICTED로 확정되지 않아도 실제로 찾아서 평가한 문서를 사용자에게 보여줘야
한다는 요청에 따라 db.fetch_evidence_reviewed를 추가했다. CONTRADICTED/UNVERIFIED
양쪽에서 평가된 문서와 applicability_check가 제대로 조회되는지 확인한다.
"""
from __future__ import annotations

from .fakes import EVAL_PARTIAL, FakeDb, FakeLiner, make_pipeline, make_result


def test_contradicted_case_exposes_reviewed_evidence_with_applicability():
    db = FakeDb()
    p = make_pipeline(db=db)  # 기본: SUPERLATIVE_FIRST + EVAL_ALL_MATCH → CONTRADICTED
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")

    v = db.fetch_verdicts(job_id)[0]
    docs = db.fetch_evidence_reviewed(v["claim_id"], v.get("canonical_id"))

    # DEFAULT_RESPONSES의 S4_HYPOTHESIS가 쿼리 2개를 내므로 문서도 2건 평가됨
    assert len(docs) == 2
    assert all(d["url"] == "https://news.example.com/a" for d in docs)
    assert all(d["applicability_check"]["scope_match"] is True for d in docs)
    assert all(d["reasoning"] for d in docs)


# 게이트를 통과 못 해 UNVERIFIED가 나와도, 실제로 찾아본 문서는 그대로 노출돼야
# 한다 — "조사를 안 한 것"과 "찾아봤지만 기준 미충족"을 구분하기 위함.
def test_unverified_case_still_exposes_reviewed_evidence():
    db = FakeDb()
    liner = FakeLiner([make_result(url="https://example.com/unrelated")])
    p = make_pipeline(db=db, liner=liner, oai_responses={"S5_EVALUATOR": EVAL_PARTIAL})
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")

    v = db.fetch_verdicts(job_id)[0]
    assert v["verdict_code"] == "UNVERIFIED"

    docs = db.fetch_evidence_reviewed(v["claim_id"], v.get("canonical_id"))
    assert len(docs) == 2  # 쿼리 2개 × 문서 1개씩
    assert all(d["applicability_check"]["timeframe_match"] is False for d in docs)  # EVAL_PARTIAL
