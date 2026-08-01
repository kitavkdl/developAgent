"""세컨드 화면 (대회 규칙 3) — Raw API Stream.

tool.call / tool.result를 가공 없이 노출한다 (API 키·헤더만 마스킹된 상태로 저장됨).
별도 SSE 서버 없이 trace_event 테이블을 폴링한다 (D-14, BUILD_PLAN §1.2):
  SELECT ... WHERE job_id=%s AND seq > %s ORDER BY seq
provider 컬럼으로 LINER/OpenAI를 색 구분 — 둘 다 실제로 쓰고 있음을 시각적으로 증명.
"""
from __future__ import annotations

import json
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from counter.settings import bridge_secrets_to_env, load_settings
from counter.ui_theme import (
    inject_theme,
    plain_chip,
    plotly_layout,
    provider_chip,
    render_snake,
)

st.set_page_config(page_title="COUNTER — Raw Trace", layout="wide")
inject_theme()
bridge_secrets_to_env()
settings = load_settings()

st.title("Raw Trace")
st.markdown(
    '<p class="ctr-lede">tool_call / tool_result를 가공 없이 노출합니다. '
    "API 키·인증 헤더만 마스킹된 상태로 저장되며, 나머지는 저장된 그대로 표시합니다.</p>",
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
    plain_chip(f"{len(events)} events", "#c5cec8") + " " +
    plain_chip("진행 중" if not terminal_seen else "종료됨",
               "#ecd089" if not terminal_seen else "#9fd9b0"),
    unsafe_allow_html=True,
)
st.write("")

# ---- 단계별 이벤트 건수 — 어느 단계가 이벤트를 가장 많이 만드는지 비교 ----
if events:
    df_ev = pd.DataFrame(events)
    df_ev["provider"] = df_ev["provider"].fillna("app")

    st.markdown('<div class="ctr-panel-header">단계별 이벤트 건수</div>',
                unsafe_allow_html=True)
    counts = df_ev["event_type"].value_counts().sort_values()
    fig2 = go.Figure(go.Bar(
        x=counts.values, y=counts.index, orientation="h",
        marker=dict(color="#c4782b"),
    ))
    plotly_layout(fig2, height=340)
    st.plotly_chart(fig2, use_container_width=True, theme=None)

    st.markdown('<div class="ctr-panel-header">파이프라인 처리 순서 (노드 클릭 시 상세로 이동)</div>',
                unsafe_allow_html=True)
    st.markdown(render_snake(events), unsafe_allow_html=True)

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
