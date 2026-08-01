"""처리 시간 단축을 위한 구조 변경의 계약 검증.

빨라지는 것 자체보다 "빨라지면서 깨지지 않는가"가 핵심이라, 각 항목마다
(a) 동시성이 실제로 걸렸는지 (b) 기존 계약(seq 단조·종료 이벤트 1회·판정 결과)이
그대로인지를 같이 본다.
"""
from __future__ import annotations

import threading
import time

import pytest

from counter.events import TraceEmitter
from counter.settings import Settings

from .fakes import DEFAULT_RESPONSES, FakeDb, FakeLiner, FakeOpenAI, make_result


def _triage_with(n: int) -> dict:
    """서로 다른 FALSIFIABLE 클레임 n건을 내놓는 S1 응답."""
    return {"claims": [{
        "claim_text": f"국내 최초 진공 블렌더 {i}",
        "normalized_text": f"국내 최초 진공 블렌더 {i}",
        "claim_category": "FALSIFIABLE", "claim_type_code": "SUPERLATIVE_FIRST",
        "missing_comparator": False, "reasoning": "최초 주장",
    } for i in range(n)]}


class _SlowOpenAI(FakeOpenAI):
    """호출마다 고정 지연 — 병렬화 여부를 벽시계로 판별하기 위한 스텁."""

    def __init__(self, responses: dict, delay: float = 0.05):
        super().__init__(responses)
        self.delay = delay
        self.concurrent = 0
        self.peak_concurrent = 0
        self._lock = threading.Lock()

    def structured(self, **kw):
        with self._lock:
            self.concurrent += 1
            self.peak_concurrent = max(self.peak_concurrent, self.concurrent)
        try:
            time.sleep(self.delay)
            return super().structured(**kw)
        finally:
            with self._lock:
                self.concurrent -= 1

    def embed_many(self, texts):
        time.sleep(self.delay)
        return super().embed_many(texts)


def _pipeline(db, oai, *, max_parallel_claims=3):
    from counter.pipeline.orchestrator import Pipeline

    return Pipeline(
        settings=Settings(job_timeout_seconds=300.0,
                          max_parallel_claims=max_parallel_claims),
        db=db, oai=oai, liner=FakeLiner([make_result()]),
    )


def _responses(n_claims: int) -> dict:
    return {**DEFAULT_RESPONSES, "S1_TRIAGE": _triage_with(n_claims)}


# ---- 클레임 병렬 처리 ----

def test_multi_claim_job_produces_one_verdict_per_claim():
    db = FakeDb()
    p = _pipeline(db, FakeOpenAI(_responses(3)))
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")

    verdicts = db.fetch_verdicts(job_id)
    assert len(verdicts) == 3
    assert {v["verdict_code"] for v in verdicts} == {"CONTRADICTED"}


def test_multi_claim_job_keeps_seq_and_terminal_contract():
    """병렬로 emit해도 seq는 1..N 빈틈없이 단조, 종료 이벤트는 정확히 1회."""
    db = FakeDb()
    p = _pipeline(db, FakeOpenAI(_responses(3)))
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")

    events = db.fetch_trace_events(job_id)
    seqs = [e["seq"] for e in events]
    assert seqs == list(range(1, len(events) + 1))

    terminals = [e["event_type"] for e in events
                 if e["event_type"] in ("job.completed", "job.failed", "job.degraded")]
    assert terminals == ["job.completed"]
    # 종료 이벤트는 반드시 마지막 — flush가 앞선 이벤트를 먼저 써야 한다
    assert events[-1]["event_type"] == "job.completed"


def test_claims_actually_run_concurrently():
    db = FakeDb()
    oai = _SlowOpenAI(_responses(3), delay=0.05)
    p = _pipeline(db, oai, max_parallel_claims=3)
    p.run_job("TEXT", "국내 최초 진공 블렌더")
    # 클레임 3건이 순차라면 어느 시점에도 동시 LLM 호출은 S2a/S2b의 2건뿐이다.
    assert oai.peak_concurrent > 2


def test_parallel_claims_are_faster_than_serial():
    def elapsed(max_parallel_claims: int) -> float:
        db = FakeDb()
        p = _pipeline(db, _SlowOpenAI(_responses(3), delay=0.05),
                      max_parallel_claims=max_parallel_claims)
        t0 = time.monotonic()
        p.run_job("TEXT", "국내 최초 진공 블렌더")
        return time.monotonic() - t0

    assert elapsed(3) < elapsed(1) * 0.8


def test_identical_claims_share_one_lane_so_canonical_is_not_duplicated():
    """normalized_text가 같은 클레임은 같은 canonical 후보 — 동시에 돌리면
    canonical이 중복 생성된다 (DB에 UNIQUE 제약이 없다). 같은 레인으로 묶여야 한다."""
    dup = {"claims": [{
        "claim_text": "국내 최초 진공 블렌더",
        "normalized_text": "국내 최초 진공 블렌더",
        "claim_category": "FALSIFIABLE", "claim_type_code": "SUPERLATIVE_FIRST",
        "missing_comparator": False, "reasoning": "최초 주장",
    } for _ in range(3)]}
    db = FakeDb()
    p = _pipeline(db, FakeOpenAI({**DEFAULT_RESPONSES, "S1_TRIAGE": dup}))
    p.run_job("TEXT", "국내 최초 진공 블렌더")

    hashes = [c["claim_hash"] for c in db.canonicals.values()]
    assert len(hashes) == len(set(hashes)) == 1


def test_claim_failure_still_ends_with_exactly_one_terminal_event():
    """한 레인이 죽어도 종료 이벤트는 job.failed 하나뿐이어야 한다."""
    class Boom(FakeOpenAI):
        def structured(self, **kw):
            if kw.get("stage") == "S4_HYPOTHESIS":
                raise RuntimeError("가설 생성 실패")
            return super().structured(**kw)

    db = FakeDb()
    p = _pipeline(db, Boom(_responses(3)))
    with pytest.raises(RuntimeError):
        p.run_job("TEXT", "국내 최초 진공 블렌더")

    events = db.fetch_trace_events(_only_job_id(db))
    terminals = [e["event_type"] for e in events
                 if e["event_type"] in ("job.completed", "job.failed", "job.degraded")]
    assert terminals == ["job.failed"]


def _only_job_id(db) -> str:
    ids = {e["job_id"] for e in db.trace_events}
    assert len(ids) == 1
    return ids.pop()


# ---- S2a/S2b 동시 실행 ----

def test_router_and_classifier_run_concurrently():
    db = FakeDb()
    oai = _SlowOpenAI(_responses(1), delay=0.05)
    p = _pipeline(db, oai)
    p.run_job("TEXT", "국내 최초 진공 블렌더")
    assert oai.peak_concurrent >= 2


def test_route_event_still_precedes_industry_event():
    """동시에 실행하더라도 trace에 남는 단계 순서는 흔들리면 안 된다."""
    db = FakeDb()
    p = _pipeline(db, FakeOpenAI(_responses(1)))
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")
    types = [e["event_type"] for e in db.fetch_trace_events(job_id)]
    assert types.index("route.decided") < types.index("industry.classified")


# ---- 비동기 trace writer ----

def test_emitter_flushes_everything_before_terminal_returns():
    db = FakeDb()
    em = TraceEmitter(db, "job-1")
    for i in range(20):
        em.emit("tool.call", {"i": i}, provider="openai")
    em.emit("job.completed", {})
    # emit이 돌아온 시점에 이미 전부 DB에 있어야 한다 (UI는 종료 이벤트를 보고 멈춘다)
    assert len(db.trace_events) == 21
    em.close()


def test_emitter_surfaces_write_error_instead_of_swallowing_it():
    class BadDb(FakeDb):
        def insert_trace_event(self, *a):
            raise RuntimeError("INSERT 실패")

    em = TraceEmitter(BadDb(), "job-2")
    em.emit("tool.call", {})
    with pytest.raises(RuntimeError, match="INSERT 실패"):
        em.flush()
    em.close()


def test_emitter_still_blocks_post_terminal_emits():
    db = FakeDb()
    em = TraceEmitter(db, "job-3")
    em.emit("job.completed", {})
    with pytest.raises(RuntimeError):
        em.emit("tool.call", {})
    em.close()


# ---- DB 헬스체크 왕복 ----

class _StubCursor:
    def __init__(self, log): self.log = log
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, params=None): self.log.append(sql)
    def fetchone(self): return {}
    def fetchall(self): return []


class _StubConn:
    closed = False

    def __init__(self, log): self.log = log
    def cursor(self, **kw): return _StubCursor(self.log)


def _stub_db(monkeypatch, probe_interval: float):
    import counter.db as dbmod

    log: list[str] = []
    monkeypatch.setattr(dbmod.psycopg2, "connect", lambda dsn: _StubConn(log))
    db = dbmod.Db(Settings(database_url="postgresql://x/y",
                           db_health_probe_interval_seconds=probe_interval))
    return db, log


def test_health_probe_is_not_issued_on_every_query(monkeypatch):
    """SELECT 1을 매 쿼리마다 돌리면 모든 DB 작업이 네트워크 왕복 2회가 된다."""
    db, log = _stub_db(monkeypatch, probe_interval=20.0)
    for i in range(10):
        db.insert_trace_event("j", i + 1, "tool.call", "openai", {})
    assert log.count("SELECT 1") == 0  # 최초 연결 직후는 유휴가 아니다
    assert len([s for s in log if s.startswith("INSERT INTO trace_event")]) == 10


def test_health_probe_still_runs_after_idle(monkeypatch):
    """유휴 뒤에는 여전히 확인한다 — Neon scale-to-zero 콜드스타트 감지 (M7)."""
    db, log = _stub_db(monkeypatch, probe_interval=0.0)
    db.insert_trace_event("j", 1, "tool.call", "openai", {})
    db.insert_trace_event("j", 2, "tool.call", "openai", {})
    assert log.count("SELECT 1") >= 1
