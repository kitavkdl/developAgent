"""공유 UI 테마 — futuristic dark, apps/web(Next.js) globals.css의 다크 모드 팔레트를
Streamlit로 이식한 버전. 세 화면(app.py, Raw Trace, Stats)이 같은 어휘(색/폰트/칩)를
쓰도록 한 곳에 모은다. 이모지는 쓰지 않는다 — 상태는 색과 라벨로만 구분한다.
"""
from __future__ import annotations

import streamlit as st

# ---- 팔레트 (apps/web/components/globals.css 다크 모드 변수 이식) ----

VERDICT_COLORS: dict[str, str] = {
    "REFUTED": "#9fd9b0",
    "NOT_REFUTED": "#ecd089",
    "PUBLIC_SUBSTANTIATION_NOT_FOUND": "#f0b4a8",
    "PUFFERY": "#c5cec8",
}

VERDICT_LABELS: dict[str, str] = {
    "REFUTED": "REFUTED — 반례 발견",
    "NOT_REFUTED": "NOT_REFUTED — 실행한 쿼리에서 반례 미발견",
    "PUBLIC_SUBSTANTIATION_NOT_FOUND": "공개 실증자료 미확인",
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

.ctr-eyebrow {{
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin: 0 0 0.35rem;
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: {INK_DIM};
}}

.ctr-eyebrow > span.dot {{
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
  background: {ACCENT};
  box-shadow: 0 0 0 4px rgba(196, 120, 43, 0.16);
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


def eyebrow(text: str) -> str:
    return f'<div class="ctr-eyebrow"><span class="dot"></span>{text}</div>'


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
