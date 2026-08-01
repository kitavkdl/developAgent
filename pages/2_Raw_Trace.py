"""세컨드 화면 (대회 규칙 3) — Raw API Stream.

tool.call / tool.result를 가공 없이 노출한다 (API 키·헤더만 마스킹된 상태로 저장됨).
별도 SSE 서버 없이 trace_event 테이블을 폴링한다 (D-14, BUILD_PLAN §1.2):
  SELECT ... WHERE job_id=%s AND seq > %s ORDER BY seq
provider 컬럼으로 LINER/OpenAI를 색 구분 — 둘 다 실제로 쓰고 있음을 시각적으로 증명.
"""
from __future__ import annotations

import json
import time

import streamlit as st

from counter.settings import bridge_secrets_to_env, load_settings

st.set_page_config(page_title="COUNTER — Raw Trace", page_icon="📡", layout="wide")
bridge_secrets_to_env()
settings = load_settings()

st.title("📡 Raw Trace (tool_call / tool_result 무가공 스트림)")

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
selected = st.selectbox("Job 선택", job_ids, index=index,
                        format_func=lambda j: f"{j[:8]}…  ({next(x['terminal_event'] or '진행 중' for x in jobs if str(x['job_id']) == j)})")
auto = st.toggle("자동 새로고침 (폴링)", value=True,
                 help=f"주기 {settings.trace_poll_interval_seconds}s — Neon 무료 티어 한도 고려해 설정값으로 관리")

PROVIDER_COLOR = {"liner": "violet", "openai": "green", "app": "gray"}

events = db.fetch_trace_events(selected, after_seq=0)
terminal_seen = any(e["event_type"] in ("job.completed", "job.failed", "job.degraded")
                    for e in events)

st.caption(f"이벤트 {len(events)}건 · 종료 이벤트 {'있음' if terminal_seen else '없음 (진행 중)'}")

for ev in events:
    provider = ev.get("provider") or "app"
    color = PROVIDER_COLOR.get(provider, "gray")
    header = f"`#{ev['seq']:03d}` :{color}[**{provider.upper()}**] — **{ev['event_type']}**"
    payload = ev["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    is_raw = ev["event_type"] in ("tool.call", "tool.result")
    highlight = payload.get("is_new") if isinstance(payload, dict) else False
    with st.expander(header + ("  🆕 신규 카테고리 생성" if highlight else ""),
                     expanded=is_raw and not terminal_seen):
        st.json(payload)  # 가공 금지 — 저장된 raw 그대로

if auto and not terminal_seen:
    time.sleep(settings.trace_poll_interval_seconds)
    st.rerun()
