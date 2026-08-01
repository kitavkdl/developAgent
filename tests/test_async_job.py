"""run_job_async — 백그라운드 스레드 실행이 스크립트 재실행/페이지 이동에도
job을 끝까지 진행시키는지 검증 (앱에서 관찰된 '이동하면 결과가 사라짐' 버그의 회귀 테스트)."""
import time

from counter.pipeline import orchestrator

from .fakes import TRIAGE_PUFFERY, FakeDb, make_pipeline


def _wait_for_terminal(db, job_id, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        events = db.fetch_trace_events(job_id)
        if any(e["event_type"] in ("job.completed", "job.failed", "job.degraded")
               for e in events):
            return events
        time.sleep(0.02)
    raise AssertionError("타임아웃 — 백그라운드 job이 끝나지 않음")


# 회귀 테스트 — run_job_async는 job.created만 즉시 기록하고, 실제 처리는
# 별도 스레드(별도 Db 커넥션)에서 끝까지 진행되어야 한다 (호출자가 바로 리턴받은 뒤
# 아무것도 더 안 해도 job은 완주해야 함 — Streamlit 스크립트가 죽는 상황의 대체 시나리오).
def test_run_job_async_completes_without_further_caller_action(monkeypatch):
    worker_db = FakeDb()
    # run_job_async 내부의 `Db(self.settings)`를 이 테스트 전용 FakeDb로 가로챈다 —
    # 실제로는 스레드 전용 psycopg2 커넥션을 새로 여는 자리.
    monkeypatch.setattr(orchestrator, "Db", lambda settings: worker_db)

    p = make_pipeline(db=FakeDb(), oai_responses={"S1_TRIAGE": TRIAGE_PUFFERY})
    job_id = p.run_job_async("TEXT", "우리 김밥이 제일 맛있다")
    assert isinstance(job_id, str) and job_id

    # 호출자가 리턴받은 뒤 그 무엇도 더 하지 않아도(=Streamlit 스크립트가 여기서
    # 죽어도) 백그라운드 스레드가 끝까지 진행되어 종료 이벤트에 도달해야 한다.
    # (스레드 스케줄링은 결정적이지 않으므로 리턴 직후의 중간 상태는 검사하지 않는다.)
    events = _wait_for_terminal(worker_db, job_id)
    assert [e["event_type"] for e in events
           if e["event_type"] in ("job.completed", "job.failed", "job.degraded")] == ["job.completed"]

    v = worker_db.fetch_verdicts(job_id)
    assert len(v) == 1 and v[0]["verdict_code"] == "PUFFERY"
