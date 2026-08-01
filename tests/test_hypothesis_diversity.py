"""S4 가설 다양성(H1/H2/H3) 회귀 테스트 — 구축 요청 [B].

SELF_REPORTED_PRIVATE_METRIC만 hypothesis_type 태그를 강제하는 별도 스키마를
쓰고, clamp_queries_diverse로 라운드로빈(SELF_CONTRADICTION 최우선) 선택을
한다. 다른 claim_type은 기존 스키마/clamp_queries 그대로라 회귀가 없어야 한다.
"""
from __future__ import annotations

from counter.pipeline.s4_hypothesis import clamp_queries_diverse, run_hypothesis
from counter.settings import Settings

from .fakes import FakeOpenAI


def _q(text, lang="ko"):
    return {"query_text": text, "language": lang}


class RecordingEmitter:
    def __init__(self):
        self.events = []

    def emit(self, event_type, payload=None, provider="app"):
        self.events.append((event_type, payload))


def test_clamp_queries_diverse_round_robins_by_type_priority():
    hypotheses = [
        {"hypothesis_type": "DEFINITION_COLLAPSE", "hypothesis": "h3",
         "queries": [_q("정의 붕괴 쿼리1"), _q("정의 붕괴 쿼리2")]},
        {"hypothesis_type": "SELF_CONTRADICTION", "hypothesis": "h1",
         "queries": [_q("자기모순 쿼리1"), _q("자기모순 쿼리2")]},
        {"hypothesis_type": "CEILING", "hypothesis": "h2",
         "queries": [_q("상한 쿼리1")]},
    ]
    queries = clamp_queries_diverse(hypotheses, budget=3)
    assert len(queries) == 3
    assert queries[0]["hypothesis_type"] == "SELF_CONTRADICTION"  # H1 최우선
    assert {q["hypothesis_type"] for q in queries} == {
        "SELF_CONTRADICTION", "CEILING", "DEFINITION_COLLAPSE"}


def test_clamp_queries_diverse_forces_required_token():
    hypotheses = [
        {"hypothesis_type": "SELF_CONTRADICTION", "hypothesis": "h1",
         "queries": [_q("누적 판매량 공식 자료")]},
    ]
    queries = clamp_queries_diverse(hypotheses, budget=3, required_token="마미케어")
    assert all("마미케어" in q["query_text"] for q in queries)


def test_clamp_queries_diverse_respects_budget_even_with_more_available():
    hypotheses = [
        {"hypothesis_type": "SELF_CONTRADICTION", "hypothesis": "h1",
         "queries": [_q(f"q{i}") for i in range(5)]},
    ]
    queries = clamp_queries_diverse(hypotheses, budget=2)
    assert len(queries) == 2


def test_run_hypothesis_uses_typed_schema_and_emits_diversity_for_self_reported():
    responses = {"S4_HYPOTHESIS": {"hypotheses": [
        {"hypothesis_type": "SELF_CONTRADICTION", "hypothesis": "h1",
         "queries": [_q("자기모순 쿼리")]},
        {"hypothesis_type": "CEILING", "hypothesis": "h2",
         "queries": [_q("상한 쿼리")]},
        {"hypothesis_type": "DEFINITION_COLLAPSE", "hypothesis": "h3",
         "queries": [_q("정의 붕괴 쿼리")]},
    ]}}
    oai = FakeOpenAI(responses)
    emitter = RecordingEmitter()
    claim = {"claim_text": "바다포도 모공앰플이 1000만개 팔림",
             "claim_type_code": "SELF_REPORTED_PRIVATE_METRIC"}
    claim_type_row = {"default_search_budget": 3}

    _hyp, queries = run_hypothesis(
        claim, "GENERAL", claim_type_row, oai, Settings(), emitter,
        delta_mode=False, date_from=None, subject={"brand": "마미케어"},
    )

    assert len(queries) == 3
    assert {q["hypothesis_type"] for q in queries} == {
        "SELF_CONTRADICTION", "CEILING", "DEFINITION_COLLAPSE"}
    assert all("마미케어" in q["query_text"] for q in queries)

    diversity = [p for t, p in emitter.events if t == "hypothesis.diversity"]
    assert len(diversity) == 1
    assert set(diversity[0]["distinct_types"]) == {
        "SELF_CONTRADICTION", "CEILING", "DEFINITION_COLLAPSE"}


def test_run_hypothesis_uses_plain_schema_for_other_claim_types():
    """target_entity 무관 claim_type은 기존 스키마/clamp_queries 그대로 —
    hypothesis_type 강제도 diversity 이벤트도 없어야 한다 (회귀 없음)."""
    responses = {"S4_HYPOTHESIS": {"hypotheses": [
        {"hypothesis": "선행 출시 사례", "what_must_exist": "더 이른 기록",
         "queries": [_q("국내 최초 진공 블렌더 2019")]},
    ]}}
    oai = FakeOpenAI(responses)
    emitter = RecordingEmitter()
    claim = {"claim_text": "국내 최초 진공 블렌더", "claim_type_code": "SUPERLATIVE_FIRST"}
    claim_type_row = {"default_search_budget": 4}

    _hyp, queries = run_hypothesis(
        claim, "GENERAL", claim_type_row, oai, Settings(), emitter,
        delta_mode=False, date_from=None, subject=None,
    )
    assert len(queries) == 1
    assert "hypothesis_type" not in queries[0]
    assert not [p for t, p in emitter.events if t == "hypothesis.diversity"]
