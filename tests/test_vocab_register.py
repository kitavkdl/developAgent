"""S4 업종별 쿼리 레지스터 회귀 테스트 — 구축 요청 [C]/[4단계].

비상장 소비재 카테고리에서 "공시/사업보고서" 같은 상장사 전용 어휘가 쿼리에
남으면 1회 재생성하고, 그래도 남으면 코드가 강제로 제거한다. 상장사/금융
카테고리(FINANCE_FINTECH)에서는 그대로 허용된다.
"""
from __future__ import annotations

from counter.pipeline.s4_hypothesis import run_hypothesis
from counter.settings import Settings

from .fakes import FakeOpenAI


class RecordingEmitter:
    def __init__(self):
        self.events = []

    def emit(self, event_type, payload=None, provider="app"):
        self.events.append((event_type, payload))


CLAIM = {"claim_text": "국내 최초 진공 블렌더", "claim_type_code": "SUPERLATIVE_FIRST"}
CLAIM_TYPE_ROW = {"default_search_budget": 4}


def _violating_response(_user):
    return {"hypotheses": [{"hypothesis": "h1", "what_must_exist": "x",
                            "queries": [{"query_text": "공시 자료 확인", "language": "ko"}]}]}


def _violating_then_clean_response(user):
    if "[재생성 사유]" in user:
        return {"hypotheses": [{"hypothesis": "h1", "what_must_exist": "x",
                                "queries": [{"query_text": "누적 판매량 상세페이지",
                                            "language": "ko"}]}]}
    return _violating_response(user)


def test_violation_triggers_one_retry_and_succeeds():
    oai = FakeOpenAI({"S4_HYPOTHESIS": _violating_then_clean_response})
    emitter = RecordingEmitter()

    _hyp, queries = run_hypothesis(
        CLAIM, "GENERAL", CLAIM_TYPE_ROW, oai, Settings(), emitter,
        delta_mode=False, date_from=None,
        category={"category_id": "BEAUTY_PERSONAL_CARE", "label": "뷰티/퍼스널케어"},
    )

    assert all("공시" not in q["query_text"] for q in queries)
    violations = [p for t, p in emitter.events if t == "hypothesis.vocab_violation"]
    assert len(violations) == 1 and violations[0]["attempt"] == 1


def test_violation_persists_after_retry_gets_stripped_by_code():
    oai = FakeOpenAI({"S4_HYPOTHESIS": _violating_response})  # 항상 위반
    emitter = RecordingEmitter()

    _hyp, queries = run_hypothesis(
        CLAIM, "GENERAL", CLAIM_TYPE_ROW, oai, Settings(), emitter,
        delta_mode=False, date_from=None,
        category={"category_id": "BEAUTY_PERSONAL_CARE", "label": "뷰티/퍼스널케어"},
    )

    assert all("공시" not in q["query_text"] for q in queries)
    violations = [p for t, p in emitter.events if t == "hypothesis.vocab_violation"]
    assert [v["attempt"] for v in violations] == [1, 2]  # 재생성도 실패 → 코드가 제거


def test_public_disclosure_category_allows_forbidden_vocab():
    oai = FakeOpenAI({"S4_HYPOTHESIS": _violating_response})
    emitter = RecordingEmitter()

    _hyp, queries = run_hypothesis(
        CLAIM, "GENERAL", CLAIM_TYPE_ROW, oai, Settings(), emitter,
        delta_mode=False, date_from=None,
        category={"category_id": "FINANCE_FINTECH", "label": "금융/핀테크"},
    )

    assert any("공시" in q["query_text"] for q in queries)  # 그대로 허용
    assert not [p for t, p in emitter.events if t == "hypothesis.vocab_violation"]


def test_no_category_defaults_to_forbidding_public_disclosure_vocab():
    oai = FakeOpenAI({"S4_HYPOTHESIS": _violating_response})
    emitter = RecordingEmitter()

    _hyp, queries = run_hypothesis(
        CLAIM, "GENERAL", CLAIM_TYPE_ROW, oai, Settings(), emitter,
        delta_mode=False, date_from=None, category=None,
    )

    assert all("공시" not in q["query_text"] for q in queries)
