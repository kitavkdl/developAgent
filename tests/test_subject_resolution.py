"""S1b 주체(브랜드) 해소 + SELF_REPORTED_PRIVATE_METRIC 회귀 테스트.

COUNTER 에이전트 튜닝 요청 [A]/[D] 검증:
- [A] 브랜드가 해소되면 이후 모든 검색 쿼리에 코드 레벨로 강제 포함되는지,
  끝내 해소 못 하면 검색을 강행하지 않고 결정론적으로 종료하는지.
- [D] SELF_REPORTED_PRIVATE_METRIC은 검색 성공 + 반례 미발견 시도
  UNVERIFIED로 끝나는지 (단, 실제 반례를 찾으면 CONTRADICTED는 여전히 유효한지).
- target_entity가 필요 없는 기존 claim_type(SUPERLATIVE_FIRST)에는 이 로직이
  전혀 개입하지 않아야 한다 (회귀 없음).
"""
from __future__ import annotations

from .fakes import EVAL_ALL_MATCH, EVAL_PARTIAL, FakeDb, FakeLiner, make_pipeline, make_result

TRIAGE_SELF_REPORTED = {
    "claims": [{
        "claim_text": "바다포도 모공앰플이 이때까지 1000만 개 이상 팔린 것",
        "normalized_text": "바다포도 모공앰플 누적 판매 1000만 개 이상",
        "claim_category": "FALSIFIABLE", "claim_type_code": "SELF_REPORTED_PRIVATE_METRIC",
        "missing_comparator": False, "reasoning": "자체 발표 누적 판매량 주장",
    }],
}

SUBJECT_NOT_FOUND = {"brand": None, "product": None, "seller": None,
                     "reasoning": "본문에 브랜드 없음"}
SUBJECT_FOUND = {"brand": "마미케어", "product": "바다포도 모공앰플", "seller": None,
                 "reasoning": "확인됨"}
SUBJECT_FOUND_FROM_SEARCH = {"brand": "마미케어", "product": "바다포도 모공앰플",
                             "seller": "자사몰", "reasoning": "검색 결과에서 확인"}


def _terminals(db, job_id):
    return [e["event_type"] for e in db.fetch_trace_events(job_id)
           if e["event_type"] in ("job.completed", "job.failed", "job.degraded")]


# [D] 회귀: 검색은 정상 성공했지만 반례를 못 찾으면 UNVERIFIED.
def test_self_reported_no_evidence_yields_unverified():
    db = FakeDb()
    liner = FakeLiner([make_result(url="https://example.com/unrelated")])
    p = make_pipeline(db=db, liner=liner, oai_responses={
        "S1_TRIAGE": TRIAGE_SELF_REPORTED,
        "S1B_SUBJECT_TEXT": SUBJECT_FOUND,
        "S5_EVALUATOR": EVAL_PARTIAL,  # timeframe_match=False → 게이트 통과 못 함
    })
    job_id = p.run_job("TEXT", "바다포도 모공앰플이 이때까지 1000만 개 이상 팔린 것")

    v = db.fetch_verdicts(job_id)
    assert len(v) == 1
    assert v[0]["verdict_code"] == "UNVERIFIED"
    assert _terminals(db, job_id) == ["job.completed"]  # degraded 아님 — 정상 판정


# CONTRADICTED는 SELF_REPORTED_PRIVATE_METRIC에서도 여전히 유효 — 타입 오버라이드는
# "반례를 못 찾았을 때"만 적용되고, 실제로 찾으면 CONTRADICTED가 우선한다.
def test_self_reported_still_allows_contradicted_when_evidence_found():
    db = FakeDb()
    liner = FakeLiner([make_result()])
    p = make_pipeline(db=db, liner=liner, oai_responses={
        "S1_TRIAGE": TRIAGE_SELF_REPORTED,
        "S1B_SUBJECT_TEXT": SUBJECT_FOUND,
        "S5_EVALUATOR": EVAL_ALL_MATCH,
    })
    job_id = p.run_job("TEXT", "바다포도 모공앰플이 이때까지 1000만 개 이상 팔린 것")
    v = db.fetch_verdicts(job_id)
    assert v[0]["verdict_code"] == "CONTRADICTED"


# [A] 회귀: 텍스트만으로 브랜드를 못 찾으면 LINER 웹 검색 1회로 재시도하고,
# 거기서 찾으면 이후 모든 검증 쿼리에 브랜드가 코드 레벨로 강제 포함돼야 한다.
def test_brand_resolved_via_search_is_forced_into_every_query():
    db = FakeDb()
    liner = FakeLiner([make_result()])
    p = make_pipeline(db=db, liner=liner, oai_responses={
        "S1_TRIAGE": TRIAGE_SELF_REPORTED,
        "S1B_SUBJECT_TEXT": SUBJECT_NOT_FOUND,
        "S1B_SUBJECT_SEARCH": SUBJECT_FOUND_FROM_SEARCH,
        "S5_EVALUATOR": EVAL_ALL_MATCH,
    })
    job_id = p.run_job("TEXT", "바다포도 모공앰플이 이때까지 1000만 개 이상 팔린 것")

    # calls[0] = 주체 해소용 web 검색, calls[1:] = S5의 실제 검증 쿼리
    assert len(liner.calls) >= 2
    verification_queries = [c["query"] for c in liner.calls[1:]]
    assert verification_queries  # S4가 실제로 쿼리를 만들어 S5까지 도달했는지
    assert all("마미케어" in q for q in verification_queries)

    v = db.fetch_verdicts(job_id)
    assert v[0]["verdict_code"] == "CONTRADICTED"


# [A] 회귀: 텍스트/검색 모두 브랜드를 못 찾으면 S4/S5를 아예 건너뛰고 결정론적으로
# 종료 — 해소 시도 1회 외의 신규 검색이 없어야 한다.
def test_unresolved_brand_skips_search_and_terminates_deterministically():
    db = FakeDb()
    liner = FakeLiner([])  # 검색해도 결과 0건 → 끝까지 못 찾음
    p = make_pipeline(db=db, liner=liner, oai_responses={
        "S1_TRIAGE": TRIAGE_SELF_REPORTED,
        "S1B_SUBJECT_TEXT": SUBJECT_NOT_FOUND,
    })
    job_id = p.run_job("TEXT", "바다포도 모공앰플이 이때까지 1000만 개 이상 팔린 것")

    assert len(liner.calls) == 1  # 해소 시도 1회만 — S4/S5 검색은 없음
    assert _terminals(db, job_id) == ["job.completed"]  # degraded 아님

    v = db.fetch_verdicts(job_id)
    assert len(v) == 1
    assert v[0]["verdict_code"] == "UNVERIFIED"
    assert v[0]["required_evidence_note"] == "주장 대상 브랜드가 특정되지 않아 검증 불가"


# 회귀 없음: target_entity가 필요 없는 기존 claim_type(SUPERLATIVE_FIRST)에는
# 주체 해소 로직이 전혀 개입하지 않는다 — 기존 CONTRADICTED 경로 그대로.
def test_target_entity_not_required_claim_types_skip_subject_resolution():
    db = FakeDb()
    liner = FakeLiner([make_result()])
    p = make_pipeline(db=db, liner=liner)  # DEFAULT_RESPONSES: TRIAGE_SUPERLATIVE
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")

    assert all(log.get("search_mode") != "subject_resolution" for log in db.search_logs)
    v = db.fetch_verdicts(job_id)
    assert v[0]["verdict_code"] == "CONTRADICTED"  # 기존 동작 그대로
