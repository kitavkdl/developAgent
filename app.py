"""COUNTER — 메인 화면 (입력 1회 → 4값 판정. 사용자 프롬프트 없음이 설계 의도).

UI는 파이프라인의 세 계약 함수(run_job / get_job_state / submit_feedback)만 안다
(BUILD_PLAN §1.1). 피드백 버튼은 결과가 이미 렌더링된 뒤에만 존재한다 —
사람이 판정을 게이트하지 않는다는 규칙(PRD N2)을 구조적으로 강제.
"""
from __future__ import annotations

import base64

import streamlit as st

from counter.settings import bridge_secrets_to_env, load_settings
from counter.ui_theme import cache_badge, inject_theme, verdict_badge

st.set_page_config(page_title="COUNTER", layout="wide")
inject_theme()
bridge_secrets_to_env()
settings = load_settings()

st.title("COUNTER")
st.markdown(
    '<p class="ctr-lede">광고 최상급 주장(국내 최초 · 업계 1위 · 임상 완료 …)의 '
    "<strong>반례가 공개 웹·학술 문헌에 실재하는지</strong> 자율적으로 찾아 보고합니다. "
    "참/거짓을 판정하지 않으며 신뢰도 점수도 만들지 않습니다 — 반례의 존재 여부만 봅니다.</p>",
    unsafe_allow_html=True,
)

# 키 없이도 앱은 뜬다 (B01 게이트). 실행 시점에만 설정을 요구.
missing = [k for k, v in {
    "OPENAI_API_KEY": settings.openai_api_key,
    "LINER_API_KEY": settings.liner_api_key,
    "DATABASE_URL": settings.database_url,
}.items() if not v]
if missing:
    st.warning(f"설정 누락: {', '.join(missing)} — `.streamlit/secrets.toml`을 채워야 판정을 실행할 수 있습니다 "
               f"(템플릿: `.streamlit/secrets.toml.example`)")


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
    with st.status("파이프라인 실행 중… (진행 원본은 trace_event — Raw Trace 페이지에서 실시간 확인)",
                   expanded=True) as status:
        try:
            job_id = pipeline.run_job(source_type, payload)
            st.session_state["last_job_id"] = job_id
            status.update(label="완료", state="complete")
        except Exception as e:
            status.update(label=f"실패: {e}", state="error")
            st.stop()

job_id = st.session_state.get("last_job_id")
if job_id:
    pipeline = get_pipeline()
    st.divider()
    st.subheader("판정 결과")
    st.caption(f"job: `{job_id}` · 상태: `{pipeline.get_job_state(job_id)}` · "
               f"Raw 스트림은 **Raw Trace** 페이지에서 확인")
    verdicts = pipeline.db.fetch_verdicts(job_id)
    if not verdicts:
        st.info("판정 결과가 아직 없습니다.")
    for v in verdicts:
        with st.container(border=True):
            st.markdown(f"**{v['claim_text']}**")
            st.markdown(verdict_badge(v["verdict_code"]), unsafe_allow_html=True)
            if v.get("confidence_source") == "cached_reuse":
                st.markdown(
                    cache_badge("HIT", v.get("search_count")) +
                    " 재검색 없이 축적된 판정을 재사용했습니다.",
                    unsafe_allow_html=True,
                )
            elif v.get("confidence_source") == "delta_search":
                st.markdown(
                    cache_badge("DELTA") +
                    " 축적된 증거 위에 시간 간극만 좁혀 재검색했습니다.",
                    unsafe_allow_html=True,
                )
            if v.get("required_evidence_note"):
                st.markdown(f"부분 증거로 종료: {v['required_evidence_note']}")
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
            if c1.button("동의", key=f"agree_{v['verdict_id']}"):
                pipeline.submit_feedback(v["verdict_id"], "AGREE")
                st.toast("피드백이 기록되었습니다.")
            if c2.button("이의", key=f"dispute_{v['verdict_id']}"):
                pipeline.submit_feedback(v["verdict_id"], "DISPUTE")
                st.toast("이의가 기록되었습니다. 임계 초과 시 다음 조회 때 자동 재검증됩니다.")
