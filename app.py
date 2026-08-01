"""COUNTER — 메인 화면 (입력 1회 → 4값 판정. 사용자 프롬프트 없음이 설계 의도).

UI는 파이프라인의 세 계약 함수(run_job / get_job_state / submit_feedback)만 안다
(BUILD_PLAN §1.1). 피드백 버튼은 결과가 이미 렌더링된 뒤에만 존재한다 —
사람이 판정을 게이트하지 않는다는 규칙(PRD N2)을 구조적으로 강제.
"""
from __future__ import annotations

import base64
import json
import time

import streamlit as st

from counter.events import TERMINAL_EVENTS
from counter.settings import bridge_secrets_to_env, load_settings
from counter.state import derive_state

st.set_page_config(page_title="COUNTER", page_icon="🔍", layout="wide")
bridge_secrets_to_env()
settings = load_settings()

st.title("🔍 COUNTER")
st.caption("광고 최상급 주장(국내 최초 / 업계 1위 / 임상 완료 …)의 **반례가 공개 웹·학술 문헌에 실재하는지** 자율적으로 찾아 보고합니다. "
           "참/거짓을 판정하지 않으며, 신뢰도 점수도 만들지 않습니다 — 반례의 존재 여부만 봅니다.")

# 키 없이도 앱은 뜬다 (B01 게이트). 실행 시점에만 설정을 요구.
missing = [k for k, v in {
    "OPENAI_API_KEY": settings.openai_api_key,
    "LINER_API_KEY": settings.liner_api_key,
    "DATABASE_URL": settings.database_url,
}.items() if not v]
if missing:
    st.warning(f"설정 누락: {', '.join(missing)} — `.streamlit/secrets.toml`을 채워야 판정을 실행할 수 있습니다 "
               f"(템플릿: `.streamlit/secrets.toml.example`)")

VERDICT_BADGE = {
    "REFUTED": ("🔴 REFUTED — 반례 발견", "red"),
    "NOT_REFUTED": ("🟡 NOT_REFUTED — 실행한 쿼리에서 반례 미발견 (사실 확인 아님)", "orange"),
    "PUBLIC_SUBSTANTIATION_NOT_FOUND": ("⚪ 공개 실증자료 미확인", "gray"),
    "PUFFERY": ("🟢 PUFFERY — 검증 대상 아님 (검색 미실행)", "green"),
}


@st.cache_resource
def get_pipeline():
    """Streamlit Cloud 배포 경로: secrets만 넣으면 첫 부팅에서 마이그레이션 +
    카테고리 centroid 시드까지 멱등 실행 (shell 접근이 없는 환경 대응)."""
    from counter.bootstrap import run_bootstrap
    from counter.pipeline.orchestrator import Pipeline

    pipeline = Pipeline()
    run_bootstrap(pipeline.db, pipeline.oai, pipeline.settings)
    return pipeline


source_type = st.radio("입력 유형", ["TEXT", "URL", "IMAGE"], horizontal=True,
                       help="스크린샷 / 링크 / 텍스트 중 하나. 프롬프트는 쓰지 않습니다.")
payload = None
if source_type == "TEXT":
    text = st.text_area("광고 문구를 붙여넣으세요", height=120,
                        placeholder="예) 국내 최초 저온압착 방식 · 판매량 1위 · 임상시험 완료")
    payload = text if text.strip() else None
elif source_type == "URL":
    url = st.text_input("광고/제품 페이지 URL", placeholder="https://...")
    payload = url if url.strip() else None
else:
    up = st.file_uploader("광고 캡처 이미지", type=["png", "jpg", "jpeg", "webp"])
    if up is not None:
        payload = (base64.b64encode(up.read()).decode(), up.type or "image/png")

run = st.button("검증 실행", type="primary", disabled=(payload is None or bool(missing)))

if run:
    pipeline = get_pipeline()
    # run_job_async는 job.created 1행만 INSERT하고 즉시 반환 — 실제 S0~S6은
    # 백그라운드 스레드에서 계속 진행되므로, 이 페이지를 벗어나거나 새로고침해도
    # job 자체는 끊기지 않는다 (예전엔 run_job()이 끝날 때까지 스크립트를 통째로
    # 블로킹해서, 그 사이 페이지를 이동하면 Streamlit이 스크립트를 죽여 결과가
    # 통째로 사라졌었다).
    job_id = pipeline.run_job_async(source_type, payload)
    st.session_state["last_job_id"] = job_id
    st.query_params["job"] = job_id  # 새로고침/새 탭에서도 job_id 복원 가능하도록 URL에도 보관
    st.rerun()

# 세션이 살아있으면 session_state, 새로고침/새 탭이면 URL의 job 파라미터로 복원
job_id = st.session_state.get("last_job_id") or st.query_params.get("job")
if job_id:
    pipeline = get_pipeline()
    st.divider()
    st.subheader("판정 결과")

    events = pipeline.db.fetch_trace_events(job_id, after_seq=0)
    terminal_seen = any(e["event_type"] in TERMINAL_EVENTS for e in events)
    state = derive_state(events)
    st.caption(f"job: `{job_id}` · 상태: `{state.value if state else '알 수 없음'}` · "
               f"Raw 스트림은 **Raw Trace** 페이지에서 확인")

    if not terminal_seen:
        st.info("⏳ 파이프라인이 백그라운드에서 처리 중입니다 — 이 탭을 벗어나거나 "
                "새로고침해도 계속 진행되니 잠시 후 다시 확인해도 됩니다.")
        time.sleep(settings.trace_poll_interval_seconds)
        st.rerun()
        st.stop()

    failed = next((e for e in events if e["event_type"] == "job.failed"), None)
    if failed:
        payload_ = failed["payload"]
        if isinstance(payload_, str):
            payload_ = json.loads(payload_)
        st.error(f"실패: {payload_.get('error', '알 수 없는 오류')}")

    verdicts = pipeline.db.fetch_verdicts(job_id)
    if not verdicts and not failed:
        st.info("판정 결과가 아직 없습니다 (검증 대상 클레임이 없었을 수 있습니다).")
    for v in verdicts:
        label, _ = VERDICT_BADGE.get(v["verdict_code"], (v["verdict_code"], "gray"))
        with st.container(border=True):
            st.markdown(f"**{v['claim_text']}**")
            st.markdown(label)
            if v.get("confidence_source") == "cached_reuse":
                st.markdown("♻️ **캐시 히트** — 재검색 없이 축적된 판정을 재사용했습니다 "
                            f"(이번 조회 검색 실행 {v['search_count']}회).")
            elif v.get("confidence_source") == "delta_search":
                st.markdown("⏱️ **델타 서치** — 축적된 증거 위에 시간 간극만 좁혀 재검색했습니다.")
            if v.get("required_evidence_note"):
                st.markdown(f"⚠️ 부분 증거로 종료: {v['required_evidence_note']}")
            st.write(v.get("reasoning") or "")
            if v.get("evidence_link"):
                st.markdown(f"**반례 문서**: [{v['evidence_link']}]({v['evidence_link']}) "
                            f"(발행일: {v.get('evidence_date') or '미상'})")
            queries = pipeline.db.fetch_executed_queries(v["claim_id"], v.get("canonical_id"))
            if queries:
                with st.expander(f"실행한 쿼리 전문 ({len(queries)}개)"):
                    for q in queries:
                        st.code(q, language=None)
            # 피드백 — 판정이 이미 출력된 뒤의 비동기 수집 (N2)
            c1, c2, _ = st.columns([1, 1, 6])
            if c1.button("👍 동의", key=f"agree_{v['verdict_id']}"):
                pipeline.submit_feedback(v["verdict_id"], "AGREE")
                st.toast("피드백이 기록되었습니다.")
            if c2.button("👎 이의", key=f"dispute_{v['verdict_id']}"):
                pipeline.submit_feedback(v["verdict_id"], "DISPUTE")
                st.toast("이의가 기록되었습니다. 임계 초과 시 다음 조회 때 자동 재검증됩니다.")
