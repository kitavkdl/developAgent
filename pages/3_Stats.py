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
st.caption("반례 '후보'는 많지만 REFUTED로 승격되는 건 소수 — scope/metric/timeframe/target "
           "필수 필드를 전부 충족해야만 코드가 REFUTED를 조립하기 때문 (PRD N1).")
g1, g2, g3 = st.columns(3)
g1.metric("평가된 후보", kpi["candidates"])
g2.metric("게이트 통과", kpi["candidates_passed"])
rate = (kpi["candidates_passed"] / kpi["candidates"] * 100) if kpi["candidates"] else 0.0
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
r1, r2, r3 = st.columns(3)
r1.metric("canonical 클레임", kpi["canonicals"])
r2.metric("누적 재사용", kpi["total_reuse"])
r3.metric("에이전트 생성 카테고리", kpi["agent_categories"])
