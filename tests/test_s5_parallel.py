"""S5 검색/평가 병렬화 회귀 테스트.

'GPT 오케스트레이션이 LINER/GPT 호출을 병렬로 진행하는지' 확인해달라는 요청에
따라 순차 루프를 2단계(검색 전부 동시 발사 → 평가 전부 동시 실행) 병렬 구조로
바꿨다. 정확성(회귀 없음)뿐 아니라 실제로 동시에 실행되는지(지연시간 단축)도
같이 검증한다 — 느린 페이크로 인위적 지연을 주고 wall-clock을 잰다.
"""
from __future__ import annotations

import time

from counter.clients.liner import SearchResponse
from counter.events import TraceEmitter
from counter.pipeline.s5_search import run_search_and_evaluate
from counter.settings import Settings

from .fakes import FakeDb, make_result


class SlowFakeLiner:
    """실제 네트워크 지연을 흉내내는 페이크 — 병렬 실행 시간 단축을 검증하기 위함."""

    def __init__(self, delay: float, n_results: int = 1):
        self.delay = delay
        self.n_results = n_results
        self.calls: list[str] = []

    def search(self, mode, query, date_from=None, max_results=10):
        self.calls.append(query)
        time.sleep(self.delay)
        results = [make_result(url=f"https://example.com/{query}-{i}")
                  for i in range(self.n_results)]
        return SearchResponse(True, "ok", "req", results,
                              {"results": [r.__dict__ for r in results]})


class SlowFakeOAI:
    """S5_EVALUATOR 호출에 인위적 지연을 주는 페이크."""

    def __init__(self, delay: float):
        self.delay = delay
        self.calls: list[str] = []

    def structured(self, *, model, effort, system, user, schema_name, schema,
                   emitter=None, stage=None):
        self.calls.append(stage)
        if emitter is not None:
            emitter.emit("tool.call", {"stage": stage}, provider="openai")
        time.sleep(self.delay)
        if emitter is not None:
            emitter.emit("tool.result", {"stage": stage}, provider="openai")
        assert stage == "S5_EVALUATOR"
        return {"scope_match": True, "metric_match": True, "timeframe_match": True,
                "target_match": True, "geography_match": True, "evidence_quote": "인용",
                "is_syndicated_copy": False, "insufficient_access": False, "reasoning": "일치"}


CLAIM = {"claim_text": "국내 최초 진공 블렌더", "claim_type_code": "SUPERLATIVE_FIRST"}
CLAIM_TYPE_ROW = {"max_evidence_per_query": 1}
FALSIFIER_SPEC = {"falsifier_spec_id": "fs1", "required_match_fields": {
    "scope": True, "metric": False, "timeframe": True,
    "target_entity": False, "geography": False}}


def _run(liner, oai, settings, db):
    emitter = TraceEmitter(db, "job-parallel-test")
    queries = [{"query_text": f"query-{i}", "language": "ko"} for i in range(4)]
    return run_search_and_evaluate(
        claim=CLAIM, claim_id="claim-1", route="GENERAL", queries=queries,
        claim_type_row=CLAIM_TYPE_ROW, falsifier_spec=FALSIFIER_SPEC,
        liner=liner, oai=oai, db=db, settings=settings, emitter=emitter,
        deadline_check=lambda: False, search_mode="full", date_from=None,
    )


# 회귀 테스트 1 — 정확성: 병렬화해도 결과 형태/개수가 그대로여야 함
def test_parallel_search_evaluate_correctness():
    db = FakeDb()
    liner = SlowFakeLiner(delay=0.01, n_results=1)
    oai = SlowFakeOAI(delay=0.01)
    settings = Settings(max_parallel_searches=4, max_parallel_evaluations=4)

    outcome = _run(liner, oai, settings, db)

    assert len(liner.calls) == 4  # 예산 내 쿼리 4개 전부 실행
    assert outcome["any_search_succeeded"] is True
    assert len(outcome["executed_queries"]) == 4
    assert len(db.search_logs) == 4
    # required_match_fields를 전부 충족하는 응답이라 최소 1개는 게이트를 통과해야 함
    assert outcome["early_stopped"] is True
    assert any(c["passed_gate"] for c in outcome["candidates"])


# 회귀 테스트 2 — 실제로 동시에 실행되는지(속도): 순차였다면 4*(search+eval) 지연이
# 그대로 누적되지만, 병렬이면 배치당 지연 1회 정도로 수렴해야 한다.
def test_parallel_search_evaluate_actually_overlaps():
    db = FakeDb()
    delay = 0.15
    liner = SlowFakeLiner(delay=delay, n_results=1)
    oai = SlowFakeOAI(delay=delay)
    settings = Settings(max_parallel_searches=4, max_parallel_evaluations=4)

    started = time.monotonic()
    _run(liner, oai, settings, db)
    elapsed = time.monotonic() - started

    sequential_worst_case = 4 * delay + 4 * delay  # 검색 4회 + 평가 4회를 전부 순차 실행했을 때
    assert elapsed < sequential_worst_case * 0.6, (
        f"elapsed={elapsed:.3f}s가 순차 실행 추정치({sequential_worst_case:.3f}s)에 "
        "근접함 — 병렬로 실행되지 않고 있을 가능성"
    )


# 회귀 테스트 3 — max_parallel_* 상한을 존중하는지 (동시 실행 개수가 설정값을 넘지 않음)
def test_respects_max_parallel_searches_cap():
    import threading

    concurrent_count = 0
    max_seen = 0
    lock = threading.Lock()

    class TrackingLiner:
        calls: list[str] = []

        def search(self, mode, query, date_from=None, max_results=10):
            nonlocal concurrent_count, max_seen
            with lock:
                concurrent_count += 1
                max_seen = max(max_seen, concurrent_count)
            time.sleep(0.05)
            with lock:
                concurrent_count -= 1
            self.calls.append(query)
            r = make_result(url=f"https://example.com/{query}")
            return SearchResponse(True, "ok", "req", [r], {"results": [r.__dict__]})

    db = FakeDb()
    oai = SlowFakeOAI(delay=0.0)
    settings = Settings(max_parallel_searches=2, max_parallel_evaluations=4)
    liner = TrackingLiner()

    _run(liner, oai, settings, db)

    assert max_seen <= 2, f"max_parallel_searches=2인데 동시 실행 {max_seen}건 관측"
