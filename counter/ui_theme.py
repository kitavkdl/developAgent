"""공유 UI 테마 — futuristic dark, apps/web(Next.js) globals.css의 다크 모드 팔레트를
Streamlit로 이식한 버전. 세 화면(app.py, Raw Trace, Stats)이 같은 어휘(색/폰트/칩)를
쓰도록 한 곳에 모은다. 이모지는 쓰지 않는다 — 상태는 색과 라벨로만 구분한다.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

# ---- 팔레트 (apps/web/components/globals.css 다크 모드 변수 이식) ----

VERDICT_COLORS: dict[str, str] = {
    "CONTRADICTED": "#9fd9b0",
    "CORROBORATED": "#b7d0f5",
    "UNVERIFIED": "#ecd089",
    "PUFFERY": "#c5cec8",
}

VERDICT_LABELS: dict[str, str] = {
    "CONTRADICTED": "CONTRADICTED — 반박 근거 발견",
    "CORROBORATED": "CORROBORATED — 뒷받침 근거 발견",
    "UNVERIFIED": "UNVERIFIED — 반증·뒷받침 근거 모두 미확인",
    "PUFFERY": "PUFFERY — 검증 대상 아님",
}

CACHE_COLORS: dict[str, str] = {
    "HIT": "#b9e0c4",
    "MISS": "#b7e0d7",
    "DELTA": "#edd49a",
    "REVERIFY": "#f0b4a8",
}

PROVIDER_COLORS: dict[str, str] = {
    "liner": "#b7d0f5",
    "openai": "#b9e0c4",
    "app": "#c5cec8",
}

_PROVIDER_LEGEND: dict[str, str] = {
    "liner": "LINER 검색 호출",
    "openai": "OpenAI 판단 호출",
    "app": "앱 내부 단계 (외부 호출 없음)",
}

INK = "#e7ebe8"
INK_DIM = "#9fb0a8"
ACCENT = "#c4782b"
ACCENT_BRIGHT = "#e2b572"
TEAL = "#1f7a6c"
TEAL_BRIGHT = "#39c2ab"
DANGER = "#f0b4a8"
OK = "#9fd9b0"
LINE_BRIGHT = "rgba(232, 220, 196, 0.18)"
PANEL_BG = "rgba(16, 36, 31, 0.82)"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Figtree:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{
  font-family: 'Figtree', ui-sans-serif, sans-serif;
}}

.stApp {{
  background:
    radial-gradient(ellipse 60% 40% at 25% 0%, rgba(196, 120, 43, 0.14), transparent 55%),
    radial-gradient(ellipse 55% 45% at 90% 15%, rgba(31, 122, 108, 0.14), transparent 50%),
    linear-gradient(180deg, #0b1714 0%, #12241f 55%, #0f1d19 100%);
  background-attachment: fixed;
  color: {INK};
}}

[data-testid="stHeader"] {{
  background: transparent;
}}

section[data-testid="stSidebar"] {{
  background: rgba(10, 22, 19, 0.92);
  border-right: 1px solid {LINE_BRIGHT};
}}

h1, h2, h3 {{
  font-family: 'Fraunces', ui-serif, serif !important;
  letter-spacing: -0.02em;
  color: #f4efe4 !important;
}}

.ctr-lede {{
  max-width: 46rem;
  color: #c5cec8;
  font-size: 0.98rem;
  line-height: 1.6;
  margin-bottom: 0.5rem;
}}

/* ---- KPI glass cards ---- */
.ctr-kpi-row {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
  margin: 0.6rem 0 1.1rem;
}}

.ctr-kpi {{
  border: 1px solid {LINE_BRIGHT};
  border-radius: 0.85rem;
  background: {PANEL_BG};
  padding: 0.85rem 1rem;
  position: relative;
  overflow: hidden;
}}

.ctr-kpi::after {{
  content: "";
  position: absolute;
  inset: -40% -40% auto auto;
  width: 6rem;
  height: 6rem;
  background: radial-gradient(circle, var(--kpi-glow, rgba(196,120,43,0.35)), transparent 70%);
  pointer-events: none;
}}

.ctr-kpi-label {{
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 0.66rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: {INK_DIM};
  margin-bottom: 0.35rem;
}}

.ctr-kpi-value {{
  font-family: 'Fraunces', ui-serif, serif;
  font-size: 1.9rem;
  font-weight: 500;
  color: #f4efe4;
  line-height: 1;
}}

.ctr-kpi-sub {{
  margin-top: 0.3rem;
  font-size: 0.74rem;
  color: {INK_DIM};
}}

/* ---- badges / chips ---- */
.ctr-badge, .ctr-chip {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  padding: 0.28rem 0.7rem;
  font-size: 0.76rem;
  font-weight: 600;
  border: 1px solid rgba(255,255,255,0.14);
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  letter-spacing: 0.01em;
}}

.ctr-panel {{
  border: 1px solid {LINE_BRIGHT};
  border-radius: 0.9rem;
  background: {PANEL_BG};
  padding: 0.9rem 1.05rem;
  margin-bottom: 0.7rem;
}}

.ctr-panel-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: {INK_DIM};
}}

/* ---- trace list ---- */
.ctr-trace {{
  border-radius: 0.6rem;
  padding: 0.5rem 0.65rem;
  margin-bottom: 0.4rem;
  background: rgba(255,255,255,0.03);
  border: 1px solid transparent;
}}

.ctr-trace.is-raw {{
  border-color: rgba(196, 120, 43, 0.35);
  background: rgba(196, 120, 43, 0.08);
}}

.ctr-trace:target {{
  border-color: {ACCENT_BRIGHT};
  background: rgba(196, 120, 43, 0.16);
  scroll-margin-top: 5rem;
}}

.ctr-trace-meta {{
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.15rem;
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 0.68rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: {INK_DIM};
}}

/* ---- snake roadmap — viewfinder 박스 체인 (파이프라인 처리 순서).
   노드 클릭 시 상세로 앵커 스크롤. 지그재그는 CSS row-reverse가 아니라
   Python 쪽에서 DOM 순서를 뒤집어 만든다 — row-reverse는 넓은 컨테이너에서
   main-start(오른쪽)부터 채워서 행이 오른쪽으로 쏠리는 버그가 있었다.

   행은 고정 N열 grid다 (flex-wrap 아님) — 열 폭이 균등해야 노드 중심이
   예측 가능해지고, 그래야 뒤에 깔리는 굵은 가이드선(rail)의 끝점을 calc()로
   정확히 계산할 수 있다. rail은 노드보다 z-index가 낮고 노드 배경은 불투명
   이므로 선이 노드를 가로지르지 않는다 — 빈 구간에만 보인다. ---- */
.ctr-snake {{
  --snake-pad: 2.6rem;      /* 행 좌우 여백 — U턴이 노드를 침범하지 않게 확보 */
  --snake-gap: 0.9rem;      /* 열 간격 — 이 틈으로만 가이드선이 보인다 */
  --snake-rail: rgba(226, 181, 114, 0.34);
  --snake-rail-dim: rgba(226, 181, 114, 0.10);
  --rail-w: 6px;
  --rail-inset: 1rem;       /* 꽉 찬 행에서 rail이 끝나는 지점 = U턴 위치 */
  display: flex;
  flex-direction: column;
  gap: 0;
  margin: 0.7rem 0 0.35rem;
  /* 좁은 폭에서 열이 노드보다 좁아지면 노드끼리 겹쳐 가이드선이 묻힌다 —
     행에 최소 폭을 주고 컨테이너를 가로 스크롤시킨다. */
  overflow-x: auto;
}}

.ctr-snake-row {{
  position: relative;
  min-width: 46rem;
  display: grid;
  grid-template-columns: repeat(var(--cols), minmax(0, 1fr));
  column-gap: var(--snake-gap);
  align-items: center;
  padding: 0.62rem var(--snake-pad);
}}

/* 가이드선 본체 — 진행 방향으로 어두운 쪽에서 밝은 쪽으로 흐른다 */
.ctr-snake-row::before {{
  content: "";
  position: absolute;
  top: 50%;
  left: var(--rail-left, var(--rail-inset));
  right: var(--rail-right, var(--rail-inset));
  height: var(--rail-w);
  transform: translateY(-50%);
  border-radius: 999px;
  background: linear-gradient(90deg, var(--snake-rail-dim), var(--snake-rail));
  z-index: 0;
}}

.ctr-snake-row.is-rtl::before {{
  background: linear-gradient(270deg, var(--snake-rail-dim), var(--snake-rail));
}}

/* 행 끝 U턴 — 이 행 중심에서 다음 행 중심까지 이어지는 "⊃" 커넥터 */
.ctr-snake-row::after {{
  content: "";
  position: absolute;
  top: 50%;
  width: 1.55rem;
  height: calc(100% + var(--rail-w));
  transform: translateY(calc(var(--rail-w) / -2));
  border: var(--rail-w) solid var(--snake-rail);
  z-index: 0;
}}

.ctr-snake-row:not(.is-rtl)::after {{
  right: var(--rail-right, var(--rail-inset));
  border-left: none;
  border-radius: 0 1.05rem 1.05rem 0;
}}

.ctr-snake-row.is-rtl::after {{
  left: var(--rail-left, var(--rail-inset));
  border-right: none;
  border-radius: 1.05rem 0 0 1.05rem;
}}

/* 마지막 행에는 U턴 대신 종료 화살촉 */
.ctr-snake-row.is-last::after {{
  width: 0;
  height: 0;
  border: none;
  border-radius: 0;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  transform: translateY(-50%);
}}

.ctr-snake-row.is-last:not(.is-rtl)::after {{
  right: calc(var(--rail-right, var(--rail-inset)) - 9px);
  left: auto;
  border-left: 11px solid var(--snake-rail);
}}

.ctr-snake-row.is-last.is-rtl::after {{
  left: calc(var(--rail-left, var(--rail-inset)) - 9px);
  right: auto;
  border-right: 11px solid var(--snake-rail);
}}

/* 시작 지점 마커 */
.ctr-snake-cap {{
  position: absolute;
  top: 50%;
  left: var(--rail-left, var(--rail-inset));
  width: 13px;
  height: 13px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: #0b1714;
  border: 3px solid var(--snake-rail);
  z-index: 0;
}}

.ctr-snake-legend {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem 1.15rem;
  padding-left: var(--snake-pad, 2.6rem);
  margin: 0 0 1.1rem;
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 0.68rem;
  letter-spacing: 0.05em;
  color: {INK_DIM};
}}

.ctr-snake-legend .swatch {{
  display: inline-block;
  width: 0.62rem;
  height: 0.62rem;
  border-radius: 2px;
  margin-right: 0.38rem;
  vertical-align: -1px;
}}

.ctr-snake-legend .rail-sample {{
  display: inline-block;
  width: 1.5rem;
  height: 4px;
  border-radius: 999px;
  margin-right: 0.38rem;
  vertical-align: 3px;
  background: linear-gradient(90deg, rgba(226,181,114,0.12), rgba(226,181,114,0.45));
}}

.ctr-snake-node {{
  position: relative;
  z-index: 1;
  justify-self: center;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 5.8rem;
  padding: 0.5rem 0.85rem;
  color: #f4efe4 !important;
  text-decoration: none !important;
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  white-space: nowrap;
  transition: transform 0.15s ease, filter 0.15s ease, background 0.15s ease;
  background: color-mix(in srgb, var(--node-color) 14%, #0a1512);
  border: 1px solid color-mix(in srgb, var(--node-color) 28%, transparent);
}}

.ctr-snake-node .corner {{
  position: absolute;
  width: 9px;
  height: 9px;
  border: 0 solid var(--node-color);
  opacity: 0.9;
}}
.ctr-snake-node .corner.tl {{ top: -1px; left: -1px; border-width: 2px 0 0 2px; }}
.ctr-snake-node .corner.tr {{ top: -1px; right: -1px; border-width: 2px 2px 0 0; }}
.ctr-snake-node .corner.bl {{ bottom: -1px; left: -1px; border-width: 0 0 2px 2px; }}
.ctr-snake-node .corner.br {{ bottom: -1px; right: -1px; border-width: 0 2px 2px 0; }}

.ctr-snake-tag {{
  font-size: 0.62rem;
  letter-spacing: 0.06em;
  color: var(--node-color);
  opacity: 0.95;
}}

.ctr-snake-label {{
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}}

.ctr-snake-node:hover {{
  filter: brightness(1.35);
  transform: translateY(-2px);
  background: color-mix(in srgb, var(--node-color) 24%, #0a1512);
  z-index: 2;
}}

/* ---- native widget restyle ---- */
.stButton > button, .stDownloadButton > button {{
  border-radius: 999px;
  border: 1px solid {LINE_BRIGHT};
  background: rgba(255,255,255,0.04);
  color: {INK};
  font-weight: 600;
}}

.stButton > button[kind="primary"] {{
  background: {ACCENT};
  border-color: {ACCENT};
  color: #1a1208;
}}

.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {{
  background: rgba(22, 48, 42, 0.65) !important;
  border-color: {LINE_BRIGHT} !important;
  color: {INK} !important;
}}

[data-testid="stExpander"] {{
  border: 1px solid {LINE_BRIGHT};
  border-radius: 0.7rem;
  background: rgba(255,255,255,0.02);
}}

[data-testid="stMetricValue"] {{
  font-family: 'Fraunces', ui-serif, serif;
  color: #f4efe4;
}}

hr {{
  border-color: {LINE_BRIGHT} !important;
}}

/* ---- alerts (st.warning / st.info / st.success / st.error) ---- */
[data-testid="stAlertContainer"] {{
  border-radius: 0.75rem !important;
  border: 1px solid {LINE_BRIGHT} !important;
  background: {PANEL_BG} !important;
}}

[data-testid="stAlertContainer"] p, [data-testid="stAlertContainer"] * {{
  color: {INK} !important;
}}

div:has(> [data-testid="stAlertContentWarning"]) [data-testid="stAlertContainer"],
[data-testid="stAlertContentWarning"] {{
  --alert-color: {ACCENT_BRIGHT};
}}

[data-testid="stAlertContentWarning"] svg {{ color: {ACCENT_BRIGHT} !important; fill: {ACCENT_BRIGHT} !important; }}
[data-testid="stAlertContentInfo"] svg {{ color: {TEAL_BRIGHT} !important; fill: {TEAL_BRIGHT} !important; }}
[data-testid="stAlertContentSuccess"] svg {{ color: {OK} !important; fill: {OK} !important; }}
[data-testid="stAlertContentError"] svg {{ color: {DANGER} !important; fill: {DANGER} !important; }}

.stAlert:has([data-testid="stAlertContentWarning"]) [data-testid="stAlertContainer"] {{
  border-color: rgba(226,181,114,0.45) !important;
  background: rgba(196,120,43,0.1) !important;
}}
.stAlert:has([data-testid="stAlertContentInfo"]) [data-testid="stAlertContainer"] {{
  border-color: rgba(57,194,171,0.4) !important;
  background: rgba(31,122,108,0.1) !important;
}}
.stAlert:has([data-testid="stAlertContentSuccess"]) [data-testid="stAlertContainer"] {{
  border-color: rgba(159,217,176,0.4) !important;
  background: rgba(47,125,76,0.12) !important;
}}
.stAlert:has([data-testid="stAlertContentError"]) [data-testid="stAlertContainer"] {{
  border-color: rgba(240,180,168,0.45) !important;
  background: rgba(179,59,44,0.12) !important;
}}

code {{
  font-family: 'IBM Plex Mono', ui-monospace, monospace !important;
}}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def verdict_badge(verdict_code: str) -> str:
    color = VERDICT_COLORS.get(verdict_code, INK_DIM)
    label = VERDICT_LABELS.get(verdict_code, verdict_code)
    return (
        f'<span class="ctr-badge" style="color:{color};'
        f'background:{color}22;border-color:{color}55;">{label}</span>'
    )


def cache_badge(decision: str | None, reused_count: int | None = None) -> str:
    if not decision:
        return ""
    color = CACHE_COLORS.get(decision, INK_DIM)
    suffix = f" · {reused_count} reused" if isinstance(reused_count, int) else ""
    return (
        f'<span class="ctr-badge" style="color:{color};'
        f'background:{color}22;border-color:{color}55;">{decision}{suffix}</span>'
    )


def provider_chip(provider: str | None) -> str:
    if not provider:
        provider = "app"
    color = PROVIDER_COLORS.get(provider, INK_DIM)
    return (
        f'<span class="ctr-chip" style="color:{color};'
        f'background:{color}18;border-color:{color}45;">{provider.upper()}</span>'
    )


def plain_chip(label: str, color: str = INK_DIM) -> str:
    return (
        f'<span class="ctr-chip" style="color:{color};'
        f'background:{color}18;border-color:{color}45;">{label}</span>'
    )


_EVENT_SHORT: dict[str, str] = {
    "job.created": "JOB START",
    "intake.completed": "INTAKE",
    "claim.extracted": "CLAIM",
    "claim.triaged": "TRIAGE",
    "route.decided": "ROUTE",
    "industry.classified": "INDUSTRY",
    "cache.decision": "CACHE",
    "tool.call": "CALL",
    "tool.result": "RESULT",
    "candidate.evaluated": "CANDIDATE",
    "verdict.assembled": "VERDICT",
    "job.completed": "DONE",
    "job.degraded": "DEGRADED",
    "job.failed": "FAILED",
}


_CORNER_SPANS = (
    '<span class="corner tl"></span><span class="corner tr"></span>'
    '<span class="corner bl"></span><span class="corner br"></span>'
)

# 행의 콘텐츠 폭 (좌우 패딩 제외) — CSS calc 안에서 쓰는 조각.
_ROW_W = "(100% - 2 * var(--snake-pad))"


def _col_edge(cols: int, k: int, side: str) -> str:
    """균등 N열 grid에서 k번째(0-base) 열의 바깥 경계까지의 거리를 CSS calc로 만든다.

    가이드선을 노드 '중심'에서 끊으면 종료 화살촉이 노드 뒤에 깔려 안 보이므로,
    열 경계(= 마지막 노드 바로 바깥의 빈 틈)에서 끊고 그 자리에 화살촉을 둔다.
    """
    col = f"(({_ROW_W} - {cols - 1} * var(--snake-gap)) / {cols})"
    if side == "right":
        return (f"calc(var(--snake-pad) + {_ROW_W} - "
                f"({col} * {k + 1} + {k} * var(--snake-gap)))")
    return f"calc(var(--snake-pad) + ({col} + var(--snake-gap)) * {k})"


def render_snake(events: list[dict], nodes_per_row: int = 6) -> str:
    """이벤트 처리 순서를 지그재그(snake) 로드맵으로 렌더링 — 노드는 viewfinder
    스타일 박스(모서리 브래킷 + #NNN 태그)로 하나씩 이어지고, 그 뒤로 굵은
    가이드선(rail)이 행을 U턴으로 연결해 읽는 순서를 끊김 없이 보여준다. 각
    노드는 해당 trace 카드(id=trace-{seq})로의 앵커 링크 — 클릭하면 상세로
    스크롤된다.

    지그재그 방향은 CSS row-reverse가 아니라 여기서 chunk 자체를 뒤집어 만든다:
    row-reverse는 main-start(넓은 컨테이너에서는 오른쪽)부터 채우기 때문에,
    실제 배포 폭(사이드바 + 넓은 본문)에서 홀수 행 전체가 오른쪽 끝에 쏠려버렸다.
    DOM 순서 자체를 뒤집고 열 배치는 항상 왼쪽부터 채우면 폭에 관계없이 정렬이
    어긋나지 않는다.

    가이드선 끝점: 행은 균등한 N열 grid이므로 k번째(0-base) 열의 중심은 콘텐츠
    폭 W에 대해 W*(k+0.5)/N이다. 마지막 행이 덜 찼을 때만 이 값으로 rail을
    잘라내면 선이 빈 칸 위로 삐져나오지 않는다. 뒤집힌 마지막 행은 노드를
    오른쪽 정렬해서 U턴(항상 행 가장자리)과 진입점이 어긋나지 않게 한다."""
    n = max(1, nodes_per_row)
    total = len(events)
    rows_html = []
    for i in range(0, total, n):
        chunk = events[i:i + n]
        row_idx = i // n
        reversed_row = bool(row_idx % 2)
        is_last = i + n >= total
        filled = len(chunk)
        ordered = list(reversed(chunk)) if reversed_row else chunk

        classes = ["ctr-snake-row"]
        if reversed_row:
            classes.append("is-rtl")
        if is_last:
            classes.append("is-last")

        style = f"--cols:{n};"
        offset = 0
        if is_last and filled < n:
            # 진행 방향의 '출구' 쪽만 마지막 노드가 놓인 열 경계에서 끊는다.
            if reversed_row:
                offset = n - filled  # 오른쪽 정렬 — 진입점(오른쪽 U턴)과 붙인다
                style += f"--rail-left:{_col_edge(n, offset, 'left')};"
            else:
                style += f"--rail-right:{_col_edge(n, filled - 1, 'right')};"

        parts = []
        if row_idx == 0:
            parts.append('<span class="ctr-snake-cap"></span>')
        for j, ev in enumerate(ordered):
            provider = ev.get("provider") or "app"
            color = PROVIDER_COLORS.get(provider, INK_DIM)
            label = _EVENT_SHORT.get(ev["event_type"], ev["event_type"])
            node_style = f"--node-color:{color};"
            if j == 0 and offset:
                node_style += f"grid-column-start:{offset + 1};"
            parts.append(
                f'<a href="#trace-{ev["seq"]}" class="ctr-snake-node" '
                f'style="{node_style}" '
                f'title="#{ev["seq"]:03d} · {ev["event_type"]} · {provider}">'
                f"{_CORNER_SPANS}"
                f'<span class="ctr-snake-tag">#{ev["seq"]:03d}</span>'
                f'<span class="ctr-snake-label">{label}</span></a>'
            )
        rows_html.append(
            f'<div class="{" ".join(classes)}" style="{style}">{"".join(parts)}</div>'
        )
    return f'<div class="ctr-snake">{"".join(rows_html)}</div>'


def snake_legend(providers: list[str]) -> str:
    """스네이크 로드맵 아래 범례 — 노드 색이 무엇을 뜻하는지, 굵은 선이 무엇인지."""
    seen = [p for p in ("app", "liner", "openai") if p in providers]
    swatches = "".join(
        f'<span><span class="swatch" style="background:{PROVIDER_COLORS[p]};"></span>'
        f"{_PROVIDER_LEGEND[p]}</span>"
        for p in seen
    )
    return (
        f'<div class="ctr-snake-legend">{swatches}'
        '<span><span class="rail-sample"></span>진행 방향 (행 끝에서 U턴)</span>'
        "<span>노드 클릭 시 아래 상세로 이동</span></div>"
    )


def kpi_row(items: list[tuple[str, object, str | None, str]]) -> None:
    """items: (label, value, sublabel, glow_hex_rgba)"""
    cards = []
    for label, value, sub, glow in items:
        sub_html = f'<div class="ctr-kpi-sub">{sub}</div>' if sub else ""
        cards.append(
            f'<div class="ctr-kpi" style="--kpi-glow:{glow};">'
            f'<div class="ctr-kpi-label">{label}</div>'
            f'<div class="ctr-kpi-value">{value}</div>'
            f"{sub_html}</div>"
        )
    st.markdown(f'<div class="ctr-kpi-row">{"".join(cards)}</div>', unsafe_allow_html=True)


def plotly_layout(fig, height: int = 340, grid: str = "both"):
    """공용 다크 테마 — verdict/cache 색상 어휘와 일치시킨 차트 스타일.

    grid: 격자를 그릴 축. 가로 막대 차트에서는 범주 축(y)의 격자가 값을 읽는 데
    아무 도움이 안 되고 노이즈만 만들므로 grid="x"로 값 축만 남긴다.
    """
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono, ui-monospace, monospace", color=INK, size=12),
        title_font=dict(family="Fraunces, ui-serif, serif", color="#f4efe4", size=16),
        legend=dict(
            bgcolor="rgba(0,0,0,0)", font=dict(color=INK_DIM, size=11),
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            # 가로 막대에서 plotly 기본 traceorder는 범례를 뒤집어 스택 순서와
            # 어긋난다 — 쌓인 순서 그대로 읽히게 고정한다.
            traceorder="normal",
        ),
        hoverlabel=dict(
            bgcolor="#12241f", bordercolor=LINE_BRIGHT, font=dict(color=INK, family="IBM Plex Mono")
        ),
    )
    fig.update_xaxes(
        showgrid=grid in ("both", "x"),
        gridcolor="rgba(232,220,196,0.08)", zerolinecolor="rgba(232,220,196,0.12)",
        linecolor="rgba(232,220,196,0.14)", automargin=True,
    )
    fig.update_yaxes(
        showgrid=grid in ("both", "y"),
        gridcolor="rgba(232,220,196,0.08)", zerolinecolor="rgba(232,220,196,0.12)",
        linecolor="rgba(232,220,196,0.14)", automargin=True,
    )
    return fig


def axis_headroom(fig, vmax: float, axis: str = "x", pad: float = 0.18,
                  integer: bool = True) -> None:
    """값 축 범위를 데이터 최대치 + 여백으로 고정 — plotly 기본 범위는 막대 끝
    바깥 라벨을 잘라먹거나, 반대로 눈금을 과하게 늘려 빈 여백만 키운다.

    건수처럼 정수만 나오는 축에서 최대치가 작으면 plotly가 0.5 단위 눈금을
    찍는데, 이벤트 1.5건 같은 눈금은 읽을 값이 아니므로 1단위로 고정한다.
    """
    top = float(vmax or 0) * (1 + pad)
    if top <= 0:
        top = 1.0
    opts: dict = {"range": [0, top]}
    if integer and float(vmax or 0) <= 8:
        opts.update(tick0=0, dtick=1)
    (fig.update_xaxes if axis == "x" else fig.update_yaxes)(**opts)


def value_labels(fig, values, categories, texts=None, orientation: str = "h") -> None:
    """막대 끝 바깥에 값 라벨을 얹는다 (스택 막대처럼 trace text를 못 쓸 때 사용).

    text 산점도는 막대와 달리 자동 여백이 없어서 값 위치에 그대로 찍으면 라벨이
    막대 끝에 붙는다 — 최대값 기준으로 살짝 띄운다.
    """
    vals = [float(v) for v in values]
    labels = list(texts) if texts is not None else [f"{v:,.0f}" for v in vals]
    pad = (max(vals) if vals else 0) * 0.035
    shifted = [v + pad for v in vals]
    if orientation == "h":
        kwargs = dict(x=shifted, y=list(categories), textposition="middle right")
    else:
        kwargs = dict(x=list(categories), y=shifted, textposition="top center")
    fig.add_trace(go.Scatter(
        mode="text", text=labels, showlegend=False, hoverinfo="skip",
        textfont=dict(family="IBM Plex Mono, ui-monospace, monospace", color=INK_DIM, size=11),
        **kwargs,
    ))
