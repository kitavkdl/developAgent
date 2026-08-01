"""단위 검증 게이트 — B03(LINER 재시도), B06(임상 강제), B08(캐시 규칙), B09(예산)."""
from datetime import datetime, timedelta, timezone

import httpx

from counter.clients.liner import LinerClient
from counter.events import TraceEmitter, mask_secrets
from counter.pipeline.s2a_router import apply_clinical_override
from counter.pipeline.s3_cache import decide_cache_action
from counter.pipeline.s4_hypothesis import clamp_queries, compute_budget
from counter.settings import Settings
from counter.state import JobState, StateMachine

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)


# B06 — CLINICAL_COMPLETION은 라우터 출력과 무관하게 SCIENTIFIC
def test_clinical_completion_forced_scientific():
    out = apply_clinical_override("CLINICAL_COMPLETION", {"route": "GENERAL", "reasoning": "x"})
    assert out["route"] == "SCIENTIFIC" and out["forced_by_code"]
    out = apply_clinical_override("RANKING", {"route": "GENERAL", "reasoning": "x"})
    assert out["route"] == "GENERAL" and not out["forced_by_code"]


# B08 — 캐시 라우팅 결정론 (ARCHITECTURE §1 S3의 4규칙)
def _canonical(days_ago=1, ttl=30, needs_reverif=False):
    return {"verified_at": NOW - timedelta(days=days_ago), "ttl_days": ttl,
            "needs_reverification": needs_reverif}


def test_cache_rules():
    assert decide_cache_action(None, now=NOW, supports_date_filter=True) == ("MISS", None)
    assert decide_cache_action(_canonical(needs_reverif=True), now=NOW,
                               supports_date_filter=True) == ("REVERIFY", None)
    assert decide_cache_action(_canonical(days_ago=5, ttl=30), now=NOW,
                               supports_date_filter=True) == ("HIT", None)
    decision, date_from = decide_cache_action(_canonical(days_ago=60, ttl=30), now=NOW,
                                              supports_date_filter=True)
    assert decision == "DELTA" and date_from is not None
    # LINER 날짜필터 미지원 → 델타 스코프 아웃, fresh/full 2-state 축소 (PRD §10-4)
    assert decide_cache_action(_canonical(days_ago=60, ttl=30), now=NOW,
                               supports_date_filter=False) == ("MISS", None)


# B09 — 예산 초과 안 함, 델타는 절반
def test_budget_clamp():
    hyps = [{"queries": [{"query_text": f"q{i}", "language": "ko"} for i in range(3)]}
            for _ in range(3)]  # 총 9개 생성
    assert len(clamp_queries(hyps, 4)) == 4
    assert compute_budget(4, delta_mode=False) == 4
    assert compute_budget(4, delta_mode=True) == 2
    assert compute_budget(3, delta_mode=True) == 2


# 상태머신 — 허용 표 밖 전이는 거부
def test_state_machine_rejects_illegal_transition():
    sm = StateMachine(JobState.INTAKE)
    sm.transition(JobState.TRIAGE)
    try:
        sm.transition(JobState.RESEARCHING)
        raise AssertionError("허용되지 않은 전이가 통과됨")
    except ValueError:
        pass


# 마스킹 — API 키/헤더는 트레이스에 노출 금지
def test_mask_secrets():
    masked = mask_secrets({"api_key": "sk-123", "Authorization": "Bearer x",
                           "query": "국내 최초", "nested": {"LINER_API_KEY": "y"}})
    assert masked["api_key"] == "***MASKED***"
    assert masked["Authorization"] == "***MASKED***"
    assert masked["nested"]["LINER_API_KEY"] == "***MASKED***"
    assert masked["query"] == "국내 최초"


# 종료 이벤트 이후 발행 금지
def test_emitter_blocks_after_terminal():
    class _Sink:
        def insert_trace_event(self, *a):  # noqa: D401
            pass

    em = TraceEmitter(_Sink(), "job-1")
    em.emit("job.created", {})
    em.emit("job.completed", {})
    try:
        em.emit("tool.call", {})
        raise AssertionError("종료 후 발행이 허용됨")
    except RuntimeError:
        pass


# B03 — LINER 429 백오프 재시도 1회 / 타임아웃 처리
def _liner_with(handler):
    settings = Settings(liner_api_key="k", liner_qps=1000.0)
    return LinerClient(settings, transport=httpx.MockTransport(handler))


def test_liner_429_then_success():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, json={"error": "rate"})
        return httpx.Response(200, json={"results": [
            {"title": "t", "url": "https://a", "snippet": "s", "date": "2020-01-01"}]},
            headers={"x-request-id": "rid-1"})

    resp = _liner_with(handler).search("web", "국내 최초")
    assert resp.ok and resp.request_id == "rid-1" and attempts["n"] == 2
    assert resp.results[0].date == "2020-01-01"


def test_liner_persistent_429_is_rate_limited():
    resp = _liner_with(lambda r: httpx.Response(429, json={})).search("web", "q")
    assert not resp.ok and resp.status == "rate_limited"


def test_liner_missing_date_stays_none():
    def handler(request):
        return httpx.Response(200, json={"results": [{"title": "t", "url": "https://a",
                                                      "snippet": "s"}]})
    resp = _liner_with(handler).search("web", "q")
    assert resp.results[0].date is None  # 날짜 추측 금지
