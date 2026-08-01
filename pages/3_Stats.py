"""통계 대시보드 (BUILD_PLAN §1.3 — 구 /v1/stats 대체).

핵심 시각화는 gate 항목: 후보는 많은데 REFUTED는 적다 = 결정론적 게이트가
오판정을 실제로 걸러내고 있다는 증거.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from counter.settings import bridge_secrets_to_env, load_settings

st.set_page_config(page_title="COUNTER — Stats", page_icon="📊", layout="wide")
bridge_secrets_to_env()
settings = load_settings()

st.title("📊 통계 대시보드")

if not settings.database_url:
    st.warning("DATABASE_URL이 설정되지 않아 통계를 표시할 수 없습니다.")
    st.stop()


@st.cache_resource
def get_db():
    from counter.db import Db

    return Db(settings)


db = get_db()
kpi = db.kpi_summary()

c1, c2, c3, c4 = st.columns(4)
c1.metric("총 판정", kpi["total_verdicts"])
c2.metric("REFUTED", kpi["refuted"])
c3.metric("캐시 히트", kpi["cache_hits"])
c4.metric("LINER 검색 실행", kpi["searches"])

st.divider()
st.subheader("🚧 결정론적 게이트 통과율")
st.caption("반례 '후보'는 많지만 REFUTED로 승격되는 건 소수 — falsifier 필수 차원"
           "(scope/metric/timeframe/target_entity/geography)을 전부 충족해야만 "
           "코드가 REFUTED를 조립하기 때문 (PRD N1, DB_SCHEMA.md §5).")
g1, g2, g3 = st.columns(3)
g1.metric("평가된 후보", kpi["candidates"])
g2.metric("REFUTED 승격", kpi["refuted"])
rate = (kpi["refuted"] / kpi["candidates"] * 100) if kpi["candidates"] else 0.0
g3.metric("통과율", f"{rate:.1f}%")

st.divider()
st.subheader("판정 분포")
breakdown = db.verdict_breakdown()
if breakdown:
    df = pd.DataFrame(breakdown).set_index("verdict_code")
    st.bar_chart(df)
else:
    st.info("판정 데이터가 아직 없습니다.")

st.divider()
st.subheader("♻️ 축적/재사용 (canonical 원장)")
r1, r2, r3, r4 = st.columns(4)
r1.metric("canonical 클레임", kpi["canonicals"])
r2.metric("누적 재사용", kpi["total_reuse"])
r3.metric("캐시 히트율", f"{float(kpi['cache_hit_ratio'] or 0) * 100:.1f}%")
r4.metric("에이전트 생성 카테고리", kpi["agent_categories"])

st.divider()
st.subheader("⏱️ 검색 모드별 (델타 서치 절감 — 축적 효과의 정량 증거)")
modes = db.search_mode_breakdown()
if modes:
    st.dataframe(pd.DataFrame(modes), hide_index=True)
else:
    st.info("검색 로그가 아직 없습니다.")

st.subheader("🩺 LINER 호출 상태별 (평가된 후보=0 원인 진단용)")
st.caption("success/empty = LINER 응답은 정상 수신 (empty면 결과 문서 0건). "
           "error/timeout = 요청 자체가 실패 (키/네트워크/엔드포인트 문제).")
statuses = db.search_status_breakdown()
if statuses:
    st.dataframe(pd.DataFrame(statuses), hide_index=True)
else:
    st.info("검색 로그가 아직 없습니다.")

st.subheader("🆕 에이전트가 즉석 생성한 카테고리 (Real-time Adaptability 증거)")
cats = db.agent_categories()
if cats:
    st.dataframe(pd.DataFrame(cats), hide_index=True)
else:
    st.info("아직 없습니다 — 시드에 없는 업종을 입력하면 여기 나타납니다.")
