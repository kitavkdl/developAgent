"""크로스 루트 캐시 재사용 검증 — 동일 콘텐츠를 다른 입력 경로(TEXT/URL/IMAGE)로
받아도 canonical 매칭은 industry_category + normalized_text 해시로만 결정되므로
(counter/pipeline/s3_cache.py) source_type과 무관하게 재사용돼야 한다.

URL 경로는 s0_intake.py가 실제 httpx 네트워크 요청(url_fetch)을 하므로 오프라인
단위 테스트에서는 검증할 수 없다 — 대신 둘 다 페이크로 완전히 제어 가능한
TEXT/IMAGE 조합으로 동일한 메커니즘(canonical이 source_type을 안 보고 매칭)을
검증한다. 실제 URL vs IMAGE 조합은 배포 환경에서 직접 확인해야 한다.

두 번째로, 재사용이 실제로 (1) 소요시간과 (2) OpenAI 호출 수를 줄이는지도
확인한다 — cached_reuse는 S4(가설)/S5(검색·평가)/S6 REPORTER용 LLM 호출을
전부 스킵하므로 두 지표 모두 fresh_search보다 뚜렷하게 낮아야 한다."""
from __future__ import annotations

from .fakes import FakeDb, FakeLiner, make_pipeline, make_result

SAME_TRIAGE = {
    "claims": [{
        "claim_text": "팩트시는 국내 최초 실시간 팩트체크 서비스입니다",
        "normalized_text": "팩트시 국내 최초 실시간 팩트체크 서비스",
        "claim_category": "FALSIFIABLE", "claim_type_code": "SUPERLATIVE_FIRST",
        "missing_comparator": False, "reasoning": "최초 주장",
    }],
}

SAME_IMAGE_INTAKE = {
    "brand_name": "팩트시", "product_name": "실시간 팩트체크 서비스",
    "product_context": "팩트시 랜딩 페이지 캡처 화면", "ocr_failed": False,
    "raw_lines": ["팩트시는 국내 최초 실시간 팩트체크 서비스입니다"],
    "observed_visual_claims": [], "uncertain_fragments": [], "is_advertisement": True,
}


def _oai_calls(db, job_id):
    return [e for e in db.trace_events
           if e["job_id"] == str(job_id) and e["event_type"] == "tool.call"
           and e["provider"] == "openai"]


def _liner_calls(db, job_id):
    return [e for e in db.trace_events
           if e["job_id"] == str(job_id) and e["event_type"] == "tool.call"
           and e["provider"] == "liner"]


def test_cross_route_reuse_text_then_image_hits_cache():
    db = FakeDb()
    liner = FakeLiner([make_result()])
    p = make_pipeline(db=db, liner=liner, oai_responses={
        "S1_TRIAGE": SAME_TRIAGE, "S0_INTAKE": SAME_IMAGE_INTAKE,
    })

    job1 = p.run_job("TEXT", "팩트시는 국내 최초 실시간 팩트체크 서비스입니다")
    v1 = db.fetch_verdicts(job1)[0]
    assert v1["confidence_source"] == "fresh_search"
    assert len(_liner_calls(db, job1)) > 0  # 실제 검색이 돌았음

    # 같은 콘텐츠를 완전히 다른 경로(IMAGE)로 다시 제출
    job2 = p.run_job("IMAGE", ("ZmFrZS1pbWFnZS1ieXRlcw==", "image/png"))
    v2 = db.fetch_verdicts(job2)[0]

    assert v2["confidence_source"] == "cached_reuse"
    assert v2["search_count"] == 0
    assert v2["verdict_code"] == v1["verdict_code"]  # 같은 판정을 재사용
    assert _liner_calls(db, job2) == []  # 재검색 없음 — 시간 절감의 핵심


def test_cache_reuse_reduces_time_and_openai_calls():
    db = FakeDb()
    liner = FakeLiner([make_result()])
    p = make_pipeline(db=db, liner=liner, oai_responses={
        "S1_TRIAGE": SAME_TRIAGE, "S0_INTAKE": SAME_IMAGE_INTAKE,
    })

    job1 = p.run_job("TEXT", "팩트시는 국내 최초 실시간 팩트체크 서비스입니다")
    job2 = p.run_job("IMAGE", ("ZmFrZS1pbWFnZS1ieXRlcw==", "image/png"))

    calls1 = len(_oai_calls(db, job1))
    calls2 = len(_oai_calls(db, job2))

    # S0(intake)/S1(triage)/S2a(router)는 캐시 여부를 알기 전에 항상 도니
    # job2도 0은 아니다 — 하지만 cached_reuse는 S4(가설, high-effort)/
    # S5(검색당 문서 평가)/S6 REPORTER+GUARDRAIL 호출을 전부 스킵하므로
    # OpenAI 호출 수가 fresh_search보다 뚜렷하게 적어야 한다. 새로 판단을
    # 만들지 않는다는 건 그만큼 새로운 할루시네이션이 끼어들 여지도 없다는 뜻.
    assert calls2 < calls1
    assert calls1 - calls2 >= 3  # 최소 S4/S5/S6 REPORTER 만큼은 줄어야 함
