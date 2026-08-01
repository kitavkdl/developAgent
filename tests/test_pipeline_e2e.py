"""파이프라인 end-to-end (Fake 주입) — T1, T3, T4, T5, T6, T10, T11 및 D-03 문구 검증."""
from counter.settings import Settings

from .fakes import (EVAL_PARTIAL, FakeDb, FakeLiner, TRIAGE_PUFFERY, make_pipeline,
                    make_result)


def _events(db, job_id):
    return db.fetch_trace_events(job_id)


def _terminals(db, job_id):
    return [e["event_type"] for e in _events(db, job_id)
            if e["event_type"] in ("job.completed", "job.failed", "job.degraded")]


# T1 — PUFFERY 입력 → 검색 tool_call 0건으로 종료 (PRD N4)
def test_puffery_zero_search_tool_calls():
    db = FakeDb()
    liner = FakeLiner([make_result()])
    p = make_pipeline(db=db, liner=liner, oai_responses={"S1_TRIAGE": TRIAGE_PUFFERY})
    job_id = p.run_job("TEXT", "우리 김밥이 제일 맛있다")
    assert liner.calls == []
    assert not any(e["provider"] == "liner" for e in _events(db, job_id))
    assert _terminals(db, job_id) == ["job.completed"]
    v = db.fetch_verdicts(job_id)
    assert len(v) == 1 and v[0]["verdict_code"] == "PUFFERY"


# 풀 파이프라인 — REFUTED (게이트 전부 충족)
def test_full_pipeline_refuted():
    db = FakeDb()
    p = make_pipeline(db=db)
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")
    v = db.fetch_verdicts(job_id)[0]
    assert v["verdict_code"] == "REFUTED"
    assert v["evidence_link"] == "https://news.example.com/a"
    assert _terminals(db, job_id) == ["job.completed"]


# T2 e2e — 필수 필드 미충족이면 REFUTED 안 됨 + D-03 문구 검증 (T7)
def test_partial_match_stays_not_refuted_with_honest_wording():
    db = FakeDb()
    p = make_pipeline(db=db, oai_responses={
        "S5_EVALUATOR": EVAL_PARTIAL,
        "S6_REPORTER": {"explanation": "이 주장이 사실임을 확인한 것이 아닙니다. "
                                        "실행한 쿼리 범위에서 반례를 찾지 못했습니다.",
                        "executed_queries": []},
    })
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")
    v = db.fetch_verdicts(job_id)[0]
    assert v["verdict_code"] == "NOT_REFUTED"
    assert v["evidence_link"] is None  # T9 상당 — Fake가 제약 위반 시 raise
    for banned in ("사실로 보입니다", "확인되었습니다", "문제없습니다"):
        assert banned not in v["explanation"]


# T3 — 같은 클레임 2회 → 2번째는 cache HIT (재검색 없음)
def test_second_run_cache_hit():
    db = FakeDb()
    liner = FakeLiner([make_result()])
    p = make_pipeline(db=db, liner=liner)
    p.run_job("TEXT", "국내 최초 진공 블렌더")
    calls_after_first = len(liner.calls)
    job2 = p.run_job("TEXT", "국내 최초 진공 블렌더")
    assert len(liner.calls) == calls_after_first  # 재검색 없음
    decisions = [e["payload"]["decision"] for e in _events(db, job2)
                 if e["event_type"] == "cache.decision"]
    assert decisions == ["HIT"]
    v = db.fetch_verdicts(job2)[0]
    assert v["cache_decision"] == "HIT" and v["verdict_code"] == "REFUTED"


# T4 — 다른 업종 파티션의 유사 문구는 canonical 매칭 안 됨 (D-08)
def test_no_cross_partition_cache_match():
    from counter.pipeline.s3_cache import run_cache_check

    db = FakeDb()
    p = make_pipeline(db=db)
    job1 = p.run_job("TEXT", "국내 최초 진공 블렌더")
    assert db.fetch_verdicts(job1)[0]["cache_decision"] == "MISS"
    claim = {"normalized_text": "국내 최초 진공 블렌더", "claim_text": "국내 최초 진공 블렌더"}
    decision, _, canonical = run_cache_check(claim, 999, [0.1, 0.2, 0.3], db, p.settings)
    assert decision == "MISS" and canonical is None  # 다른 category_id → 매칭 불가


# T5 — 유사도 임계 미달 → 신규 카테고리 생성 후 정상 판정
def test_new_category_created_when_below_threshold():
    db = FakeDb()
    db.categories = [{"id": 1, "code": "cosmetics_beauty", "label_ko": "화장품/뷰티",
                      "created_by": "seed", "similarity": 0.10}]  # 임계(0.75) 미달
    p = make_pipeline(db=db)
    job_id = p.run_job("TEXT", "드론 방제 국내 최초")
    classified = [e for e in _events(db, job_id) if e["event_type"] == "industry.classified"]
    assert classified and classified[0]["payload"]["is_new"] is True
    assert any(c["created_by"] == "agent_generated" for c in db.categories)
    assert db.fetch_verdicts(job_id)[0]["verdict_code"] == "REFUTED"  # 판정은 정상


# T6 — LINER 전면 타임아웃 → DEGRADED 결정론적 종료 (무한 스피너 없음)
def test_liner_timeout_degrades_deterministically():
    db = FakeDb()
    p = make_pipeline(db=db, liner=FakeLiner(status="timeout"))
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")
    assert _terminals(db, job_id) == ["job.degraded"]
    v = db.fetch_verdicts(job_id)[0]
    assert v["verdict_code"] == "PUBLIC_SUBSTANTIATION_NOT_FOUND"
    assert v["degraded_reason"]


# T10/T15 — 피드백은 응답 이후 비동기, dispute 임계 초과 → 재검증 플래그 → REVERIFY
def test_feedback_dispute_triggers_reverification():
    db = FakeDb()
    settings = Settings(job_timeout_seconds=300.0,
                        dispute_count_threshold=3, dispute_ratio_threshold=0.3)
    p = make_pipeline(db=db, settings=settings)
    job1 = p.run_job("TEXT", "국내 최초 진공 블렌더")
    verdict = db.fetch_verdicts(job1)[0]  # 응답은 피드백 없이 이미 완료 (N2)
    assert db.feedback == []
    for _ in range(3):
        p.submit_feedback(verdict["id"], "DISPUTE")
    canonical = next(iter(db.canonicals.values()))
    assert canonical["needs_reverification"] is True
    job2 = p.run_job("TEXT", "국내 최초 진공 블렌더")
    decisions = [e["payload"]["decision"] for e in _events(db, job2)
                 if e["event_type"] == "cache.decision"]
    assert decisions == ["REVERIFY"]  # 풀 재검색


# T11 — JOB_TIMEOUT_SECONDS 초과 → DEGRADED 결정론적 종료 (D-13)
def test_job_timeout_degrades():
    db = FakeDb()
    p = make_pipeline(db=db, settings=Settings(job_timeout_seconds=0.0))
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")
    assert _terminals(db, job_id) == ["job.degraded"]
    v = db.fetch_verdicts(job_id)[0]
    assert "JOB_TIMEOUT_SECONDS" in (v["degraded_reason"] or "")


# 종료 이벤트 정확히 1회 (BUILD_PLAN §1.2)
def test_terminal_event_exactly_once():
    db = FakeDb()
    p = make_pipeline(db=db)
    job_id = p.run_job("TEXT", "국내 최초 진공 블렌더")
    assert len(_terminals(db, job_id)) == 1
    seqs = [e["seq"] for e in _events(db, job_id)]
    assert seqs == sorted(seqs) and len(seqs) == len(set(seqs))  # 단조 증가
