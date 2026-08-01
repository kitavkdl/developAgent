"""통계 대시보드 (BUILD_PLAN §1.3 — 구 /v1/stats 대체).

핵심 시각화는 gate 항목: 후보는 많은데 REFUTED는 적다 = 결정론적 게이트가
오판정을 실제로 걸러내고 있다는 증거. 차트들은 전부 "비교/대조" 축으로 구성한다 —
후보 vs 승격, 캐시 재사용 vs 신규 검색, 풀 서치 vs 델타 서치 비용.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from counter.settings import bridge_secrets_to_env, load_settings
from counter.ui_theme import (
    ACCENT,
    ACCENT_BRIGHT,
    TEAL_BRIGHT,
    VERDICT_COLORS,
    eyebrow,
    inject_theme,
    kpi_row,
    plotly_layout,
)

st.set_page_config(page_title="COUNTER — Stats", layout="wide")
inject_theme()
bridge_secrets_to_env()
settings = load_settings()

st.markdown(eyebrow("Evidence-memory analytics"), unsafe_allow_html=True)
st.title("통계 대시보드")
st.markdown(
    '<p class="ctr-lede">숫자를 대조해서 판단합니다 — 후보 대비 승격률, '
    "재사용 대비 신규 검색, 풀 서치 대비 델타 서치 비용. 각 차트는 "
    "결정론적 게이트와 축적 캐시가 실제로 작동한다는 근거를 보여줍니다.</p>",
    unsafe_allow_html=True,
)

if not settings.database_url:
    st.warning("DATABASE_URL이 설정되지 않아 통계를 표시할 수 없습니다.")
    st.stop()


@st.cache_resource
def get_db():
    from counter.db import Db

    return Db(settings)


db = get_db()
kpi = db.kpi_summary()

kpi_row([
    ("총 판정", kpi["total_verdicts"], None, "rgba(196,120,43,0.35)"),
    ("REFUTED", kpi["refuted"], "반례 확정 건수", "rgba(159,217,176,0.35)"),
    ("캐시 히트", kpi["cache_hits"], "재검색 없이 재사용", "rgba(31,122,108,0.35)"),
    ("LINER 검색 실행", kpi["searches"], None, "rgba(183,208,245,0.35)"),
])

st.divider()

# ---- 1. 결정론적 게이트 통과율: 후보 vs 승격 (funnel) ----
st.subheader("결정론적 게이트 통과율")
st.caption(
    "반례 '후보'는 많지만 REFUTED로 승격되는 건 소수 — falsifier 필수 차원"
    "(scope/metric/timeframe/target_entity/geography)을 전부 충족해야만 "
    "코드가 REFUTED를 조립하기 때문 (PRD N1, DB_SCHEMA.md §5)."
)

g1, g2, g3 = st.columns([1, 1, 1.4])
rate = (kpi["refuted"] / kpi["candidates"] * 100) if kpi["candidates"] else 0.0
with g1:
    kpi_row([("평가된 후보", kpi["candidates"], None, "rgba(196,120,43,0.3)")])
with g2:
    kpi_row([("REFUTED 승격", kpi["refuted"], None, "rgba(159,217,176,0.3)")])
with g3:
    kpi_row([("게이트 통과율", f"{rate:.1f}%", "낮을수록 게이트가 엄격하게 걸러낸다는 뜻", "rgba(226,181,114,0.3)")])

funnel = go.Figure(go.Funnel(
    y=["평가된 후보", "REFUTED 승격"],
    x=[kpi["candidates"], kpi["refuted"]],
    textinfo="value+percent initial",
    marker=dict(color=[ACCENT, "#9fd9b0"]),
    connector=dict(line=dict(color="rgba(232,220,196,0.25)", width=1)),
))
plotly_layout(funnel, height=280)
st.plotly_chart(funnel, use_container_width=True, theme=None)

st.divider()

# ---- 2. 판정 분포 (네 값 taxonomy 전체를 항상 보여줌) ----
st.subheader("판정 분포")
breakdown = db.verdict_breakdown()
codes = list(VERDICT_COLORS.keys())
counts_by_code = {r["verdict_code"]: r["n"] for r in breakdown}
values = [counts_by_code.get(c, 0) for c in codes]

fig_v = go.Figure(go.Bar(
    x=values, y=codes, orientation="h",
    marker=dict(color=[VERDICT_COLORS[c] for c in codes]),
    text=values, textposition="outside",
))
plotly_layout(fig_v, height=300)
fig_v.update_xaxes(title="판정 건수")
st.plotly_chart(fig_v, use_container_width=True, theme=None)

st.divider()

# ---- 3. 축적/재사용: canonical 원장 ----
st.subheader("축적 / 재사용 (canonical 원장)")
r1, r2 = st.columns([1, 1.2])
with r1:
    kpi_row([
        ("canonical 클레임", kpi["canonicals"], None, "rgba(196,120,43,0.3)"),
        ("누적 재사용", kpi["total_reuse"], None, "rgba(159,217,176,0.3)"),
        ("캐시 히트율", f"{float(kpi['cache_hit_ratio'] or 0) * 100:.1f}%", None, "rgba(31,122,108,0.3)"),
        ("에이전트 생성 카테고리", kpi["agent_categories"], None, "rgba(226,181,114,0.3)"),
    ])
with r2:
    donut = go.Figure(go.Pie(
        labels=["재사용된 조회", "최초 조회 (member_count 기준 추정)"],
        values=[kpi["total_reuse"], max(kpi["canonicals"], 1)],
        hole=0.62,
        marker=dict(colors=[TEAL_BRIGHT, "rgba(255,255,255,0.12)"]),
        textinfo="label+percent",
    ))
    plotly_layout(donut, height=280)
    donut.update_layout(showlegend=False)
    st.plotly_chart(donut, use_container_width=True, theme=None)

st.divider()

# ---- 4. 검색 모드별 비교 — 델타 서치 절감 정량 증거 ----
st.subheader("검색 모드별 비교 (델타 서치 절감 효과)")
st.caption("건수와 평균 지연시간을 나란히 대조합니다 — 델타/재사용 모드가 "
          "풀 서치보다 저렴하다면 축적 효과가 실제로 비용을 줄이고 있다는 뜻입니다.")
modes = db.search_mode_breakdown()
if modes:
    df_modes = pd.DataFrame(modes)
    df_modes["avg_latency_ms"] = df_modes["avg_latency_ms"].astype(float).round(0)

    fig_m = go.Figure()
    fig_m.add_trace(go.Bar(
        x=df_modes["search_mode"], y=df_modes["n"], name="실행 건수",
        marker=dict(color=ACCENT), yaxis="y1",
    ))
    fig_m.add_trace(go.Scatter(
        x=df_modes["search_mode"], y=df_modes["avg_latency_ms"], name="평균 지연시간 (ms)",
        mode="lines+markers", marker=dict(color=TEAL_BRIGHT, size=10),
        line=dict(color=TEAL_BRIGHT, width=2), yaxis="y2",
    ))
    fig_m.update_layout(
        yaxis=dict(title="실행 건수"),
        yaxis2=dict(title="평균 지연시간 (ms)", overlaying="y", side="right",
                   showgrid=False),
    )
    plotly_layout(fig_m, height=340)
    st.plotly_chart(fig_m, use_container_width=True, theme=None)
else:
    st.info("검색 로그가 아직 없습니다.")

st.divider()

# ---- 5. 에이전트가 즉석 생성한 카테고리 — 실시간 적응력 증거 ----
st.subheader("에이전트가 즉석 생성한 카테고리 (Real-time Adaptability 증거)")
st.caption("시드에 없는 업종을 입력하면 여기 누적됩니다 — 우상향할수록 "
          "미리 정의되지 않은 업종에도 스스로 대응하고 있다는 뜻입니다.")
cats = db.agent_categories()
if cats:
    df_cats = pd.DataFrame(cats).sort_values("created_at")
    df_cats["cumulative"] = range(1, len(df_cats) + 1)

    fig_c = go.Figure(go.Scatter(
        x=df_cats["created_at"], y=df_cats["cumulative"],
        mode="lines+markers", line=dict(color=ACCENT_BRIGHT, shape="hv", width=2),
        marker=dict(color=ACCENT_BRIGHT, size=7),
        fill="tozeroy", fillcolor="rgba(226,181,114,0.12)",
    ))
    fig_c.update_yaxes(title="누적 카테고리 수")
    plotly_layout(fig_c, height=300)
    st.plotly_chart(fig_c, use_container_width=True, theme=None)

    st.dataframe(df_cats[["category_id", "label", "created_at"]], hide_index=True,
                use_container_width=True)
else:
    st.info("아직 없습니다 — 시드에 없는 업종을 입력하면 여기 나타납니다.")
