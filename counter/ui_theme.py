"""공유 UI 테마 — futuristic dark, apps/web(Next.js) globals.css의 다크 모드 팔레트를
Streamlit로 이식한 버전. 세 화면(app.py, Raw Trace, Stats)이 같은 어휘(색/폰트/칩)를
쓰도록 한 곳에 모은다. 이모지는 쓰지 않는다 — 상태는 색과 라벨로만 구분한다.
"""
from __future__ import annotations

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
   main-start(오른쪽)부터 채워서 행이 오른쪽으로 쏠리는 버그가 있었다. ---- */
.ctr-snake {{
  display: flex;
  flex-direction: column;
  gap: 1.3rem;
  margin: 0.7rem 0 1.2rem;
}}

.ctr-snake-row {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}}

.ctr-snake-arrow {{
  flex: 0 0 auto;
  color: {INK_DIM};
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 0.8rem;
  opacity: 0.55;
}}

.ctr-snake-node {{
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  flex: 0 0 auto;
  min-width: 6.5rem;
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


def render_snake(events: list[dict], nodes_per_row: int = 6) -> str:
    """이벤트 처리 순서를 지그재그(snake) 로드맵으로 렌더링 — 노드는 viewfinder
    스타일 박스(모서리 브래킷 + #NNN 태그)로 하나씩 이어진다. 각 노드는 해당
    trace 카드(id=trace-{seq})로의 앵커 링크 — 클릭하면 상세로 스크롤된다.

    지그재그 방향은 CSS row-reverse가 아니라 여기서 chunk 자체를 뒤집어 만든다:
    row-reverse는 main-start(넓은 컨테이너에서는 오른쪽)부터 채우기 때문에,
    실제 배포 폭(사이드바 + 넓은 본문)에서 홀수 행 전체가 오른쪽 끝에 쏠려버렸다.
    DOM 순서 자체를 뒤집고 flex-direction은 항상 기본값(row)으로 두면 모든 행이
    컨테이너 왼쪽부터 채워지므로 폭에 관계없이 정렬이 어긋나지 않는다."""
    rows_html = []
    for i in range(0, len(events), nodes_per_row):
        chunk = events[i:i + nodes_per_row]
        row_idx = i // nodes_per_row
        reversed_row = bool(row_idx % 2)
        arrow = "←" if reversed_row else "→"
        ordered = list(reversed(chunk)) if reversed_row else chunk
        parts = []
        for j, ev in enumerate(ordered):
            provider = ev.get("provider") or "app"
            color = PROVIDER_COLORS.get(provider, INK_DIM)
            label = _EVENT_SHORT.get(ev["event_type"], ev["event_type"])
            if j > 0:
                parts.append(f'<span class="ctr-snake-arrow">{arrow}</span>')
            parts.append(
                f'<a href="#trace-{ev["seq"]}" class="ctr-snake-node" '
                f'style="--node-color:{color};" '
                f'title="#{ev["seq"]:03d} · {ev["event_type"]} · {provider}">'
                f"{_CORNER_SPANS}"
                f'<span class="ctr-snake-tag">#{ev["seq"]:03d}</span>'
                f'<span class="ctr-snake-label">{label}</span></a>'
            )
        rows_html.append(f'<div class="ctr-snake-row">{"".join(parts)}</div>')
    return f'<div class="ctr-snake">{"".join(rows_html)}</div>'


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


def plotly_layout(fig, height: int = 340):
    """공용 다크 테마 — verdict/cache 색상 어휘와 일치시킨 차트 스타일."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono, ui-monospace, monospace", color=INK, size=12),
        title_font=dict(family="Fraunces, ui-serif, serif", color="#f4efe4", size=16),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=INK_DIM)),
        hoverlabel=dict(
            bgcolor="#12241f", bordercolor=LINE_BRIGHT, font=dict(color=INK, family="IBM Plex Mono")
        ),
    )
    fig.update_xaxes(
        gridcolor="rgba(232,220,196,0.08)", zerolinecolor="rgba(232,220,196,0.12)",
        automargin=True,
    )
    fig.update_yaxes(
        gridcolor="rgba(232,220,196,0.08)", zerolinecolor="rgba(232,220,196,0.12)",
        automargin=True,
    )
    return fig
