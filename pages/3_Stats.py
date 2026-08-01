"""통계 대시보드 (BUILD_PLAN §1.3 — 구 /v1/stats 대체).

핵심 시각화는 gate 항목: 후보는 많은데 CONTRADICTED는 적다 = 결정론적 게이트가
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
    DANGER,
    INK_DIM,
    LINE_BRIGHT,
    OK,
    TEAL_BRIGHT,
    VERDICT_COLORS,
    axis_headroom,
    inject_theme,
    kpi_row,
    plain_chip,
    plotly_layout,
)

st.set_page_config(page_title="COUNTER — Stats", layout="wide")
inject_theme()
bridge_secrets_to_env()
settings = load_settings()

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
if not hasattr(db, "reuse_savings_summary"):
    # 배포 직후 st.cache_resource가 (get_db() 자체 코드는 안 바뀌어) 캐시를
    # 무효화하지 않고 코드 변경 전에 만들어진 낡은 Db 객체를 그대로 들고 있을 수
    # 있다 — 캐시를 비우고 최신 클래스로 즉시 재생성해 재부팅 없이도 자가 치유한다.
    get_db.clear()
    db = get_db()

kpi = db.kpi_summary()

kpi_row([
    ("총 판정", kpi["total_verdicts"], None, "rgba(196,120,43,0.35)"),
    ("CONTRADICTED", kpi["contradicted"], "반박 근거 확정 건수", "rgba(159,217,176,0.35)"),
    ("CORROBORATED", kpi["corroborated"], "뒷받침 근거 확정 건수", "rgba(183,208,245,0.35)"),
    ("캐시 히트", kpi["cache_hits"], "재검색 없이 재사용", "rgba(31,122,108,0.35)"),
    ("LINER 검색 실행", kpi["searches"], None, "rgba(183,208,245,0.35)"),
])

st.divider()

# ---- 1. 결정론적 게이트 통과율: 후보 vs 승격 (funnel) ----
st.subheader("결정론적 게이트 통과율")
st.caption(
    "반례 '후보'는 많지만 CONTRADICTED로 승격되는 건 소수 — falsifier 필수 차원"
    "(scope/metric/timeframe/target_entity/geography)을 전부 충족해야만 코드가 "
    "CONTRADICTED를 조립하기 때문 (PRD N1, DB_SCHEMA.md §5). 반증도 뒷받침도 "
    "못 찾으면 UNVERIFIED — '진실이다'로 오해되지 않도록 별도 코드로 둔다."
)

g1, g2, g3 = st.columns([1, 1, 1.4])
rate = (kpi["contradicted"] / kpi["candidates"] * 100) if kpi["candidates"] else 0.0
with g1:
    kpi_row([("평가된 후보", kpi["candidates"], None, "rgba(196,120,43,0.3)")])
with g2:
    kpi_row([("CONTRADICTED 승격", kpi["contradicted"], None, "rgba(159,217,176,0.3)")])
with g3:
    kpi_row([("게이트 통과율", f"{rate:.1f}%", "낮을수록 게이트가 엄격하게 걸러낸다는 뜻", "rgba(226,181,114,0.3)")])

# 2단계 퍼널은 사실상 막대 두 개였다 — 게이트가 "무엇을 걸러냈는지"가 안 보인다.
# 후보 전체를 하나의 막대로 두고 승격분/차단분을 나란히 쌓으면 걸러낸 양 자체가
# 면적으로 읽힌다.
blocked = max(kpi["candidates"] - kpi["contradicted"], 0)
gate = go.Figure()
gate.add_trace(go.Bar(
    x=[kpi["contradicted"]], y=["평가된 후보"], orientation="h",
    name=f"CONTRADICTED 승격 ({kpi['contradicted']:,})",
    marker=dict(color=VERDICT_COLORS["CONTRADICTED"]),
    hovertemplate="승격 %{x}건<extra></extra>",
))
gate.add_trace(go.Bar(
    x=[blocked], y=["평가된 후보"], orientation="h",
    name=f"게이트에서 차단 ({blocked:,})",
    marker=dict(color="rgba(196,120,43,0.42)",
                line=dict(color="rgba(226,181,114,0.5)", width=1)),
    hovertemplate="차단 %{x}건<extra></extra>",
))
gate.update_layout(barmode="stack", bargap=0.62)
gate.update_yaxes(showticklabels=False)
gate.update_xaxes(title="반례 후보 건수")
plotly_layout(gate, height=190, grid="x")
st.plotly_chart(gate, use_container_width=True, theme=None)

st.divider()

# ---- 2. 판정 분포 (taxonomy 전체를 항상 보여줌) ----
st.subheader("판정 분포")
st.caption("건수(막대)와 구성비(상단 띠)를 같이 봅니다 — 코드별 절대량과 "
           "'전체에서 차지하는 비중'은 서로 다른 질문이라 하나로는 답이 안 됩니다.")
breakdown = db.verdict_breakdown()
codes = list(VERDICT_COLORS.keys())
counts_by_code = {r["verdict_code"]: r["n"] for r in breakdown}
values = [counts_by_code.get(c, 0) for c in codes]
total_v = sum(values)

if total_v:
    # 100% 구성 띠 — 판정 체계 전체가 어떤 비율로 나뉘는지 한 줄로 읽힌다.
    comp = go.Figure()
    for code, val in zip(codes, values):
        if not val:
            continue
        share = val / total_v * 100
        comp.add_trace(go.Bar(
            x=[share], y=["구성비"], orientation="h", name=code,
            marker=dict(color=VERDICT_COLORS[code]),
            text=[f"{share:.0f}%" if share >= 7 else ""],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(color="#0b1714", size=11),
            hovertemplate=f"{code} %{{x:.1f}}% ({val:,}건)<extra></extra>",
        ))
    comp.update_layout(barmode="stack", bargap=0.55)
    comp.update_yaxes(showticklabels=False)
    comp.update_xaxes(showticklabels=False, range=[0, 100])
    plotly_layout(comp, height=130, grid="none")
    st.plotly_chart(comp, use_container_width=True, theme=None)

fig_v = go.Figure(go.Bar(
    x=values, y=codes, orientation="h",
    marker=dict(color=[VERDICT_COLORS[c] for c in codes]),
    text=[f"{v:,}" + (f"  ({v / total_v * 100:.0f}%)" if total_v else "") for v in values],
    textposition="outside",
    textfont=dict(color=INK_DIM, size=11),
    hovertemplate="%{y} %{x}건<extra></extra>",
))
fig_v.update_layout(bargap=0.42)
plotly_layout(fig_v, height=280, grid="x")
axis_headroom(fig_v, max(values) if values else 0, pad=0.3)
fig_v.update_xaxes(title="판정 건수")
st.plotly_chart(fig_v, use_container_width=True, theme=None)

st.divider()

# ---- 3. 축적/재사용: canonical 원장 ----
st.subheader("축적 / 재사용 (canonical 원장)")
kpi_row([
    ("canonical 클레임", kpi["canonicals"], None, "rgba(196,120,43,0.3)"),
    ("누적 재사용", kpi["total_reuse"], None, "rgba(159,217,176,0.3)"),
    ("에이전트 생성 카테고리", kpi["agent_categories"], None, "rgba(226,181,114,0.3)"),
])

hit_ratio = max(0.0, min(1.0, float(kpi["cache_hit_ratio"] or 0)))

gauge_col, note_col = st.columns([1, 1.15])
with gauge_col:
    gauge = go.Figure(go.Pie(
        values=[hit_ratio, 1 - hit_ratio],
        hole=0.74,
        sort=False,
        direction="clockwise",
        marker=dict(
            colors=[TEAL_BRIGHT, "#1c3831"],
            line=dict(color=LINE_BRIGHT, width=1),
        ),
        textinfo="none",
        hoverinfo="skip",
    ))
    gauge.add_annotation(
        text=f"{hit_ratio * 100:.1f}%", showarrow=False, y=0.56,
        font=dict(family="Fraunces, ui-serif, serif", size=30, color="#f4efe4"),
    )
    gauge.add_annotation(
        text="캐시 히트율", showarrow=False, y=0.38,
        font=dict(family="IBM Plex Mono, ui-monospace, monospace", size=11, color="#9fb0a8"),
    )
    plotly_layout(gauge, height=260)
    gauge.update_layout(showlegend=False, margin=dict(l=8, r=8, t=8, b=8))
    st.plotly_chart(gauge, use_container_width=True, theme=None)
with note_col:
    st.caption(
        "재사용된 조회가 전체 조회(member_count)에서 차지하는 비율입니다 — "
        "반복 조회일수록 새 검색 없이 축적된 판정을 재사용했다는 뜻입니다."
    )
    st.markdown(
        plain_chip(f"재사용 {kpi['total_reuse']}건", TEAL_BRIGHT) + " " +
        plain_chip(f"canonical {kpi['canonicals']}건", "#c5cec8"),
        unsafe_allow_html=True,
    )

st.divider()

# ---- 4. 재사용 절감 효과 (시간 · LLM 호출 수) ----
st.subheader("재사용 절감 효과 (시간 · LLM 호출 수)")
st.caption(
    "cached_reuse는 S4(가설)~S6(REPORTER/GUARDRAIL)까지 새 LLM 판단을 전혀 "
    "만들지 않고 이미 검증된 판정을 그대로 재사용합니다 — 소요시간뿐 아니라 "
    "'매번 새로 판단해서 생기는 할루시네이션 여지' 자체가 줄어듭니다. 다른 "
    "입력 경로(TEXT/URL/IMAGE)로 받아도 canonical 매칭은 업종·정규화된 "
    "클레임 문구로만 되므로 source_type과 무관하게 재사용됩니다."
)
savings = db.reuse_savings_summary()
if savings:
    fresh = next((r for r in savings if r["confidence_source"] == "fresh_search"), None)
    cached = next((r for r in savings if r["confidence_source"] == "cached_reuse"), None)

    if fresh and cached and fresh.get("avg_job_ms"):
        time_saved = (1 - float(cached["avg_job_ms"] or 0) / float(fresh["avg_job_ms"])) * 100
        fresh_calls = max(float(fresh["avg_openai_calls"] or 0), 1e-9)
        call_saved = (1 - float(cached["avg_openai_calls"] or 0) / fresh_calls) * 100
        kpi_row([
            ("캐시 재사용 시 평균 소요시간 절감", f"{time_saved:.0f}%", None, "rgba(31,122,108,0.3)"),
            ("캐시 재사용 시 평균 LLM 호출 절감", f"{call_saved:.0f}%", None, "rgba(31,122,108,0.3)"),
        ])

        # 표 대신 같은 축에 나란히 놓은 막대 — 절감폭이 길이 차이로 바로 읽힌다.
        # 소요시간(ms)과 호출 수는 단위가 달라 한 축에 못 얹으므로 두 차트로 나눈다.
        rows = [("fresh_search", fresh), ("cached_reuse", cached)]
        panels = [
            ("평균 소요시간 (ms)", "avg_job_ms", "{:,.0f} ms"),
            ("평균 OpenAI 호출 수", "avg_openai_calls", "{:,.1f} 회"),
        ]
        cols = st.columns(2)
        for col, (panel_title, field, fmt) in zip(cols, panels):
            names = [n for n, _ in rows]
            vals = [float(r[field] or 0) for _, r in rows]
            fig_sv = go.Figure(go.Bar(
                x=vals, y=names, orientation="h",
                marker=dict(color=[ACCENT, TEAL_BRIGHT]),
                text=[fmt.format(v) for v in vals], textposition="outside",
                textfont=dict(color=INK_DIM, size=11),
                hovertemplate="%{y} · %{x:.1f}<extra></extra>",
            ))
            fig_sv.update_layout(bargap=0.45, title=dict(text=panel_title, x=0, font=dict(size=13)))
            plotly_layout(fig_sv, height=200, grid="x")
            axis_headroom(fig_sv, max(vals), pad=0.35)
            col.plotly_chart(fig_sv, use_container_width=True, theme=None)

    with st.expander("판정 경로별 원자료"):
        df_savings = pd.DataFrame(savings).rename(columns={
            "confidence_source": "판정 경로", "n": "건수",
            "avg_job_ms": "평균 소요시간(ms)", "avg_openai_calls": "평균 OpenAI 호출 수",
        })
        st.dataframe(df_savings, hide_index=True, use_container_width=True)
else:
    st.info("완료된 job이 아직 없습니다.")

st.divider()

# ---- 5. 검색 모드별 비교 — 델타 서치 절감 정량 증거 ----
st.subheader("검색 모드별 비교 (델타 서치 절감 효과)")
st.caption("건수와 평균 지연시간을 나란히 대조합니다 — 델타/재사용 모드가 "
          "풀 서치보다 저렴하다면 축적 효과가 실제로 비용을 줄이고 있다는 뜻입니다. "
          "두 지표는 단위가 다르므로 이중 축에 겹치지 않고 같은 순서의 별도 차트로 둡니다.")
modes = db.search_mode_breakdown()
if modes:
    df_modes = pd.DataFrame(modes)
    df_modes["avg_latency_ms"] = df_modes["avg_latency_ms"].astype(float).round(0)
    df_modes = df_modes.sort_values("n", ascending=False)

    # 이중 축(건수 막대 + 지연시간 선)은 두 축의 눈금을 임의로 맞춰야 해서
    # "선이 막대 위/아래" 라는 착시를 만든다. 같은 x 순서를 공유하는 차트 둘로
    # 나누면 비교는 그대로 되면서 그 착시가 사라진다.
    m_cols = st.columns(2)
    mode_panels = [
        ("실행 건수", df_modes["n"].astype(float), ACCENT, "{:,.0f}건"),
        ("평균 지연시간 (ms)", df_modes["avg_latency_ms"], TEAL_BRIGHT, "{:,.0f}ms"),
    ]
    for col, (panel_title, series, color, fmt) in zip(m_cols, mode_panels):
        fig_m = go.Figure(go.Bar(
            x=df_modes["search_mode"], y=series,
            marker=dict(color=color),
            text=[fmt.format(v) for v in series], textposition="outside",
            textfont=dict(color=INK_DIM, size=11),
            hovertemplate="%{x} · %{y:,.0f}<extra></extra>",
        ))
        fig_m.update_layout(bargap=0.5,
                            title=dict(text=panel_title, x=0, font=dict(size=13)))
        plotly_layout(fig_m, height=300, grid="y")
        axis_headroom(fig_m, float(series.max()), axis="y", pad=0.28)
        col.plotly_chart(fig_m, use_container_width=True, theme=None)
else:
    st.info("검색 로그가 아직 없습니다.")

st.divider()

# ---- 6. LINER 호출 상태별 (평가된 후보=0 원인 진단용) ----
st.subheader("LINER 호출 상태별")
st.caption("success/empty = LINER 응답은 정상 수신 (empty면 결과 문서 0건). "
           "error/timeout = 요청 자체가 실패 (키/네트워크/엔드포인트 문제).")
statuses = db.search_status_breakdown()
if statuses:
    status_colors = {"success": OK, "empty": INK_DIM, "timeout": ACCENT_BRIGHT, "error": DANGER}
    df_status = pd.DataFrame(statuses).sort_values("n")
    total_s = float(df_status["n"].sum()) or 1.0
    fig_s = go.Figure(go.Bar(
        x=df_status["n"], y=df_status["status"], orientation="h",
        marker=dict(color=[status_colors.get(s, INK_DIM) for s in df_status["status"]]),
        text=[f"{n:,}  ({n / total_s * 100:.0f}%)" for n in df_status["n"]],
        textposition="outside", textfont=dict(color=INK_DIM, size=11),
        hovertemplate="%{y} · %{x}건<extra></extra>",
    ))
    fig_s.update_layout(bargap=0.42)
    plotly_layout(fig_s, height=max(200, 42 * len(df_status) + 90), grid="x")
    axis_headroom(fig_s, float(df_status["n"].max()), pad=0.3)
    fig_s.update_xaxes(title="호출 건수")
    st.plotly_chart(fig_s, use_container_width=True, theme=None)
else:
    st.info("검색 로그가 아직 없습니다.")

st.divider()

# ---- 7. 에이전트가 즉석 생성한 카테고리 — 실시간 적응력 증거 ----
st.subheader("에이전트가 즉석 생성한 카테고리")
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
        customdata=df_cats["label"],
        hovertemplate="%{customdata}<br>누적 %{y}개<extra></extra>",
    ))
    # 마지막 지점에 현재 누적치를 붙여둔다 — 축만 봐서는 "지금 몇 개인지"가 안 읽힌다.
    fig_c.add_annotation(
        x=df_cats["created_at"].iloc[-1], y=int(df_cats["cumulative"].iloc[-1]),
        text=f"누적 {int(df_cats['cumulative'].iloc[-1])}개", showarrow=False,
        xanchor="right", yanchor="bottom", yshift=10,
        font=dict(family="IBM Plex Mono, ui-monospace, monospace",
                  color=ACCENT_BRIGHT, size=12),
    )
    fig_c.update_yaxes(title="누적 카테고리 수",
                       range=[0, int(df_cats["cumulative"].iloc[-1]) * 1.3 + 0.5])
    plotly_layout(fig_c, height=300, grid="y")
    st.plotly_chart(fig_c, use_container_width=True, theme=None)

    st.dataframe(
        df_cats[["category_id", "label", "created_at"]].rename(columns={
            "category_id": "카테고리 코드", "label": "라벨", "created_at": "생성 시각",
        }),
        hide_index=True, use_container_width=True,
    )
else:
    st.info("아직 없습니다 — 시드에 없는 업종을 입력하면 여기 나타납니다.")
