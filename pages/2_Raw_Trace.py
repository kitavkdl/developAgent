"""세컨드 화면 (대회 규칙 3) — Raw API Stream.

tool.call / tool.result를 가공 없이 노출한다 (API 키·헤더만 마스킹된 상태로 저장됨).
별도 SSE 서버 없이 trace_event 테이블을 폴링한다 (D-14, BUILD_PLAN §1.2):
  SELECT ... WHERE job_id=%s AND seq > %s ORDER BY seq
provider 컬럼으로 LINER/OpenAI를 색 구분 — 둘 다 실제로 쓰고 있음을 시각적으로 증명.

화면 순서는 "결론 먼저, 과정은 그 아래"다: job을 고르면 그 job이 무엇을
판정했고 근거가 무엇이었는지(counter/ui_verdict.py — 메인 화면과 동일한 카드)를
맨 위에 보여주고, 그 뒤에 이벤트 통계·처리 순서·raw payload가 온다. 이 화면의
목적은 과정 노출이지만, 과정만 먼저 나오면 "그래서 결과가 뭔데"를 확인하려고
매번 스크롤을 끝까지 내려야 했다.
"""
from __future__ import annotations

import json
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from counter.settings import bridge_secrets_to_env, load_settings
from counter.ui_theme import (
    PROVIDER_COLORS,
    axis_headroom,
    inject_theme,
    kpi_row,
    plain_chip,
    plotly_layout,
    provider_chip,
    render_snake,
    snake_legend,
    value_labels,
)
from counter.ui_verdict import render_verdict_cards

st.set_page_config(page_title="COUNTER — Raw Trace", layout="wide")
inject_theme()
bridge_secrets_to_env()
settings = load_settings()

st.title("Raw Trace")
st.markdown(
    '<p class="ctr-lede">선택한 job이 <strong>무엇을 판정했고 근거가 무엇이었는지</strong>를 '
    "먼저 보여주고, 그 아래에 그 결론에 이른 처리 과정을 가공 없이 노출합니다. "
    "tool_call / tool_result는 API 키·인증 헤더만 마스킹된 상태로 저장되며, "
    "나머지는 저장된 그대로 표시합니다.</p>",
    unsafe_allow_html=True,
)

if not settings.database_url:
    st.warning("DATABASE_URL이 설정되지 않아 스트림을 표시할 수 없습니다.")
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

jobs = db.fetch_recent_jobs(limit=20)
if not jobs:
    st.info("아직 실행된 job이 없습니다.")
    st.stop()

default_job = st.session_state.get("last_job_id")
job_ids = [str(j["job_id"]) for j in jobs]
index = job_ids.index(default_job) if default_job in job_ids else 0

col_select, col_toggle = st.columns([3, 1])
with col_select:
    selected = st.selectbox(
        "Job 선택", job_ids, index=index,
        format_func=lambda j: f"{j[:8]}…  ({next(x['terminal_event'] or '진행 중' for x in jobs if str(x['job_id']) == j)})",
    )
with col_toggle:
    auto = st.toggle("자동 새로고침", value=True,
                     help=f"주기 {settings.trace_poll_interval_seconds}s — Neon 무료 티어 한도 고려해 설정값으로 관리")

events = db.fetch_trace_events(selected, after_seq=0)
terminal_seen = any(e["event_type"] in ("job.completed", "job.failed", "job.degraded")
                    for e in events)

st.markdown(
    plain_chip(f"이벤트 {len(events)}건", "#c5cec8") + " " +
    plain_chip("진행 중" if not terminal_seen else "종료됨",
               "#ecd089" if not terminal_seen else "#9fd9b0"),
    unsafe_allow_html=True,
)
st.write("")

# ---- 결론 먼저 — 이 job이 무엇을 판정했고 근거가 무엇이었는지 ----
# (메인 화면과 같은 카드를 그린다. 아래 처리 과정은 이 결론에 이른 경로다.)
st.subheader("이 job이 내린 결론")

failed = next((e for e in events if e["event_type"] == "job.failed"), None)
if failed:
    failed_payload = failed["payload"]
    if isinstance(failed_payload, str):
        failed_payload = json.loads(failed_payload)
    st.error(f"실패: {failed_payload.get('error', '알 수 없는 오류')}")

# 폴링 비용: 진행 중인 job은 verdict가 아직 없어 이 쿼리 1건만 늘고, 카드마다
# 붙는 추가 조회(실행 쿼리/검토 문서)는 판정이 생긴 뒤 — 즉 폴링이 이미 멈춘
# 뒤 — 에만 실행된다. Neon 무료 티어 한도에 실질적인 영향은 없다.
verdicts = db.fetch_verdicts(selected)
if verdicts:
    render_verdict_cards(db, verdicts)
elif not terminal_seen:
    st.info("아직 판정이 나오지 않았습니다 — 아래 처리 과정이 진행 중입니다.")
elif not failed:
    st.info("이 job에서는 판정이 생성되지 않았습니다 (검증 대상 클레임이 없었을 수 있습니다).")

st.divider()
st.subheader("결론에 이른 처리 과정")

# ---- 단계별 이벤트 건수 — 어느 단계가 어느 provider를 써서 이벤트를 만드는지 ----
if events:
    df_ev = pd.DataFrame(events)
    df_ev["provider"] = df_ev["provider"].fillna("app")

    provider_counts = df_ev["provider"].value_counts()
    kpi_row([
        ("LINER 호출", int(provider_counts.get("liner", 0)), "검색 tool 이벤트",
         "rgba(183,208,245,0.35)"),
        ("OpenAI 호출", int(provider_counts.get("openai", 0)), "LLM 판단 이벤트",
         "rgba(185,224,196,0.35)"),
        ("앱 내부 단계", int(provider_counts.get("app", 0)), "외부 호출 없는 단계",
         "rgba(197,206,200,0.3)"),
        ("단계 종류", int(df_ev["event_type"].nunique()), None, "rgba(196,120,43,0.35)"),
    ])

    st.markdown('<div class="ctr-panel-header">단계별 이벤트 건수 (provider 구성)</div>',
                unsafe_allow_html=True)
    st.caption("한 막대 안의 색 구성이 그 단계가 실제로 어느 API를 썼는지 보여줍니다 — "
               "LINER와 OpenAI가 둘 다 실행되었다는 증거입니다.")

    pivot = (df_ev.pivot_table(index="event_type", columns="provider",
                               values="seq", aggfunc="count", fill_value=0))
    totals = pivot.sum(axis=1).sort_values()
    pivot = pivot.loc[totals.index]

    fig2 = go.Figure()
    for prov in ("app", "liner", "openai"):
        if prov not in pivot.columns:
            continue
        fig2.add_trace(go.Bar(
            x=pivot[prov], y=pivot.index, orientation="h",
            name=prov.upper(), marker=dict(color=PROVIDER_COLORS[prov]),
            hovertemplate="%{y} · " + prov.upper() + " %{x}건<extra></extra>",
        ))
    fig2.update_layout(barmode="stack", bargap=0.35)
    value_labels(fig2, totals.values, totals.index)
    plotly_layout(fig2, height=max(280, 34 * len(totals) + 90), grid="x")
    axis_headroom(fig2, totals.max())
    fig2.update_xaxes(title="이벤트 건수")
    st.plotly_chart(fig2, use_container_width=True, theme=None)

    st.markdown('<div class="ctr-panel-header">파이프라인 처리 순서</div>',
                unsafe_allow_html=True)
    st.markdown(render_snake(events), unsafe_allow_html=True)
    st.markdown(snake_legend(list(provider_counts.index)), unsafe_allow_html=True)

st.divider()

for ev in events:
    provider = ev.get("provider") or "app"
    is_raw = ev["event_type"] in ("tool.call", "tool.result")
    payload = ev["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    highlight = payload.get("is_new") if isinstance(payload, dict) else False

    st.markdown(
        f'<div id="trace-{ev["seq"]}" class="ctr-trace {"is-raw" if is_raw else ""}">'
        f'<div class="ctr-trace-meta">'
        f'<span>#{ev["seq"]:03d}</span> {provider_chip(provider)} '
        f'<strong style="color:#e7ebe8;text-transform:none;letter-spacing:0;">{ev["event_type"]}</strong>'
        f'{plain_chip("신규 카테고리 생성", "#e2b572") if highlight else ""}'
        f"</div></div>",
        unsafe_allow_html=True,
    )
    with st.expander("payload", expanded=is_raw and not terminal_seen):
        st.json(payload)  # 가공 금지 — 저장된 raw 그대로

if auto and not terminal_seen:
    time.sleep(settings.trace_poll_interval_seconds)
    st.rerun()
