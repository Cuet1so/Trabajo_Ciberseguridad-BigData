"""Sistema visual compartido: colores semánticos, paneles y formato Plotly."""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

INK = "#16263D"
MUTED = "#52647B"
BLUE = "#2864DD"
GATEWAY_COLORS = {"Ámbar": "#946008", "Cobalto": BLUE}
# Los grupos tienen una paleta distinta a la de las pasarelas; sus ID son arbitrarios.
CLUSTER_COLORS = {"0": "#128378", "1": "#6753C5", "2": "#B93F65"}
PLOT_CONFIG = {"displaylogo": False, "scrollZoom": False, "toImageButtonOptions": {"scale": 2}}

CSS = """
<style>
:root{--ink:#16263d;--muted:#52647b;--line:#e0e6ef;--accent:#2864dd}
.block-container{max-width:1560px;padding:4rem 2rem 2.5rem}
[data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"]{gap:.9rem}
h1,h2,h3{letter-spacing:-.025em}
[data-testid="stMain"] h3{font-size:1.12rem;padding:0;line-height:1.45}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{font-size:.88rem;line-height:1.5;color:var(--muted)}
[data-testid="stCaptionContainer"]{opacity:1}
[data-testid="stMetric"]{padding:0}
[data-testid="stMetricLabel"] p{font-size:.9rem;font-weight:600;color:var(--muted)}
[data-testid="stMetricValue"]{font-size:1.9rem;font-weight:650;letter-spacing:-.045em;color:var(--ink)}
[data-testid="stMetricDelta"]{font-size:.9rem}
[data-testid="stMain"] [class*="st-key-panel_"],[data-testid="stMain"] [class*="st-key-summary_"]{background:white;border-radius:10px}
[data-testid="stMain"] [class*="st-key-summary_"]{min-height:160px;gap:.45rem}
[data-testid="stMain"] .st-key-summary_cobalto{border-top:3px solid #2864dd}
[data-testid="stMain"] .st-key-summary_ambar{border-top:3px solid #946008}
[data-testid="stMain"] .st-key-summary_fallos{border-top:3px solid #8d9bb0}
[data-testid="stMain"] .st-key-summary_control{border-top:3px solid #946008}
[data-testid="stMain"] .st-key-summary_events{border-top:3px solid #128378}
[role="tablist"]{gap:6px;background:#e9eef6;padding:5px;border-radius:10px;border:1px solid #e0e6ef}
[role="tab"]{height:42px;border-radius:7px;padding:0 18px;font-weight:600;background:transparent;flex:1;justify-content:center}
[role="tab"][aria-selected="true"]{background:#fff;color:#2057c8;box-shadow:0 1px 3px #17325a13}
[role="tab"] .react-aria-SelectionIndicator{display:none}
:is(button, input, [role="combobox"], [role="tab"], summary):focus-visible{outline:2px solid #2864dd;outline-offset:2px}
[role="tabpanel"]{padding-top:1rem}
[data-testid="stSidebar"]{border-right:0}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding-top:1.3rem}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p{color:#b8c6dc}
[data-testid="stSidebar"] h3{font-size:.95rem;letter-spacing:0}
[data-testid="stSidebar"] hr{border-color:#314361}
[data-testid="stSidebar"] [data-testid="stExpander"] details{border-color:#314361}
.brand{display:flex;align-items:center;gap:12px;margin:0 0 22px}
.brand-mark{background:#2864dd;color:#fff;border-radius:10px;width:40px;height:40px;display:grid;place-items:center;font-size:20px;font-weight:700}
.brand-name{font-size:1rem;font-weight:700;letter-spacing:.09em;color:#fff;line-height:1.4}
.brand-sub{font-size:.8rem;color:#b8c6dc}
.page-header{display:flex;justify-content:space-between;align-items:center;gap:1rem;margin-bottom:.2rem}
.eyebrow{font-size:.76rem;font-weight:700;letter-spacing:.11em;text-transform:uppercase;color:#52647b;margin-bottom:.25rem}
.page-header h1{font-size:1.7rem;line-height:1.2;padding:0;margin:0;color:#16263d}
.page-subtitle{color:#52647b;font-size:.96rem;margin:.35rem 0 .25rem}
.context-badge{white-space:nowrap;border:1px solid #d8e3ef;border-radius:6px;background:white;color:#52647b;font-size:.82rem;padding:7px 11px}
.insight{display:flex;gap:16px;align-items:center;border-left:4px solid #2864dd;background:#eaf1ff;padding:11px 16px;border-radius:0 9px 9px 0}
.insight-title{font-size:1rem;font-weight:650;color:#163c78;margin:0 0 4px}
.insight-body{font-size:.92rem;color:#345477;line-height:1.5}
.panel-note{font-size:.85rem;line-height:1.5;color:#52647b;margin-top:2px}
.group-card{border:1px solid #e0e6ef;border-left:4px solid var(--group);border-radius:8px;padding:13px 15px;margin-bottom:10px;background:#fff}
.group-name{font-size:.88rem;font-weight:700;color:var(--group);margin-bottom:5px}
.group-value{font-size:1.35rem;font-weight:650;color:#16263d}
.group-body{font-size:.87rem;color:#52647b;line-height:1.55}
.legend-pill{display:inline-block;font-size:.85rem;font-weight:600;padding:4px 9px;border-radius:4px;margin-right:6px}
@media(max-width:760px){.block-container{padding:4rem 1rem 2rem}.page-header{align-items:flex-start}.page-header h1{font-size:1.4rem}.context-badge{display:none}[role="tab"]{padding:0 8px;flex:none}[role="tab"] p{font-size:.82rem}[data-testid="stMetricValue"]{font-size:1.65rem}[data-testid="stMain"] [class*="st-key-summary_"]{min-height:0}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_header() -> None:
    st.markdown('<div class="page-header"><div><div class="eyebrow">Computación Masiva para Big Data · Trabajo 5</div>'
                '<h1>Observatorio de autenticación</h1></div><span class="context-badge">Análisis local · Datos sintéticos</span></div>'
                '<p class="page-subtitle">Del volumen de fallos al alcance sobre las cuentas. Ámbar como referencia; Cobalto bajo observación.</p>',
                unsafe_allow_html=True)


def insight(title: str, body: str) -> None:
    st.markdown(f'<div class="insight"><div><div class="insight-title">{escape(title)}</div>'
                f'<div class="insight-body">{escape(body)}</div></div></div>', unsafe_allow_html=True)


def chart_style(fig: go.Figure, *, height: int = 330, legend: bool = True) -> go.Figure:
    fig.update_layout(template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font={"family": "Arial, sans-serif", "size": 14, "color": MUTED},
                      separators=",.", margin={"l": 12, "r": 18, "t": 25, "b": 14},
                      legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0, "title": None,
                              "font": {"size": 12}, "traceorder": "normal"}, showlegend=legend,
                      hoverlabel={"bgcolor": "#16263D", "font": {"color": "white", "size": 14}},
                      modebar={"orientation": "h"}, uirevision="preserve-view")
    fig.update_xaxes(showgrid=False, zeroline=False, automargin=True, title_font={"size": 13}, tickfont={"size": 12})
    fig.update_yaxes(gridcolor="#e9eef5", zeroline=False, automargin=True, title_font={"size": 13}, tickfont={"size": 12})
    return fig


def plot(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, width="stretch", key=key, config=PLOT_CONFIG, theme=None)
