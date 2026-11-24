"""Figuras de presentación: solo leen datos ya calculados del experimento."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from bi_metrics import PERIOD_NAMES, PROFILE_NAMES
from config import GATEWAYS
from ui_theme import CLUSTER_COLORS, GATEWAY_COLORS, INK, chart_style


def morris_evolution(history: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for gateway in GATEWAYS:
        for prefix, title, dash in (("real", "CSV exacto", "solid"), ("morris", "Morris", "dot")):
            fig.add_trace(go.Scatter(x=history.instante, y=history[f"{prefix}_{gateway}"], mode="lines",
                                    name=f"{gateway} · {title}", line={"color": GATEWAY_COLORS[gateway], "dash": dash, "width": 2.5},
                                    hovertemplate="%{x|%d/%m %H:%M}<br>%{y:,.0f} intentos fallidos<extra>%{fullData.name}</extra>"))
    chart_style(fig, height=350)
    fig.update_layout(yaxis_title="Intentos fallidos acumulados", hovermode="x unified")
    fig.update_yaxes(tickformat=",.0f")
    fig.update_xaxes(type="date", tickformat="%d/%m\n%H:%M", nticks=5)
    return fig


def morris_error(history: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for gateway in GATEWAYS:
        exact = history[f"real_{gateway}"]
        relative = 100*(history[f"morris_{gateway}"]-exact).abs().div(exact.where(exact.ne(0))).fillna(0)
        fig.add_trace(go.Scatter(x=history.instante, y=relative, name=gateway, mode="lines",
                                line={"color": GATEWAY_COLORS[gateway], "width": 2.5},
                                hovertemplate="%{x|%d/%m %H:%M}<br>Error: %{y:.2f} %<extra>%{fullData.name}</extra>"))
    chart_style(fig, height=350)
    fig.update_layout(yaxis_title="Error absoluto / exacto (%)", hovermode="x unified")
    fig.update_yaxes(rangemode="tozero", ticksuffix=" %")
    fig.update_xaxes(type="date", tickformat="%d/%m\n%H:%M", nticks=4)
    return fig


def umap_map(points: pd.DataFrame, all_points: pd.DataFrame, centers: np.ndarray | None, groups: list[int]) -> go.Figure:
    data = points.copy()
    data["grupo"] = data.cluster.astype(str)
    data["fase"] = np.where(data.id <= 300, "Ajuste inicial", "Transformación posterior")
    fig = px.scatter(data, x="umap_x", y="umap_y", color="grupo", symbol="grupo",
                     symbol_map={"0": "circle", "1": "diamond", "2": "square"},
                     color_discrete_map=CLUSTER_COLORS, category_orders={"grupo": ["0", "1", "2"]},
                     custom_data=["id", "instante", "pasarela", "fallos", "cuentas", "ips_origen", "cluster", "fase", "perfil"],
                     render_mode="webgl", opacity=.65)
    fig.update_traces(marker={"size": 5}, hovertemplate=(
        "<b>Grupo %{customdata[6]} · %{customdata[2]}</b><br>"
        "ID %{customdata[0]} · %{customdata[7]}<br>Instante: %{customdata[1]}<br>"
        "Fallos/min: %{customdata[3]}<br>Cuentas/min: %{customdata[4]}<br>IP/min: %{customdata[5]}<br>"
        "Perfil real (auditoría): %{customdata[8]}<extra></extra>"))
    for trace in fig.data:
        trace.name = f"Grupo {trace.name}"
    if centers is not None:
        for group in groups:
            xy = centers[group]
            fig.add_trace(go.Scattergl(x=[xy[0]], y=[xy[1]], name=f"Centroide {group}", mode="markers+text",
                                      text=[f"C{group}"], textposition="top right", textfont={"color": INK, "size": 13},
                                      marker={"symbol": "x", "size": 14, "color": INK, "line": {"color": "white", "width": 2}},
                                      showlegend=False, hovertemplate=f"<b>Centroide {group}</b><br>Fijo desde el evento 300<br>UMAP 1: %{{x:.3f}}<br>UMAP 2: %{{y:.3f}}<extra></extra>"))
    chart_style(fig, height=440)
    fig.update_layout(xaxis_title="UMAP 1", yaxis_title="UMAP 2", legend={"title": None})
    # El plano mantiene los mismos límites al cambiar los filtros; no se recalcula UMAP.
    for feature, axis in (("umap_x", "xaxis"), ("umap_y", "yaxis")):
        low, high = float(all_points[feature].min()), float(all_points[feature].max())
        if centers is not None:
            values = centers[:, 0 if feature == "umap_x" else 1]
            low, high = min(low, float(values.min())), max(high, float(values.max()))
        pad = max((high-low)*.12, .5)
        fig.update_layout(**{axis: {"range": [low-pad, high+pad]}})
    return fig


def profile_heatmap(cross: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Heatmap(z=cross.to_numpy(), x=[PROFILE_NAMES[p] for p in cross.columns],
                              y=[f"Grupo {int(c)}" for c in cross.index], zmin=0, zmax=100,
                              colorscale=[[0, "#F0F4FA"], [.5, "#A8C6F7"], [1, "#2864DD"]],
                              texttemplate="%{z:.1f} %", textfont={"size": 15}, showscale=False,
                              xgap=5, ygap=5, hovertemplate="%{y}<br>%{x}: %{z:.2f} % del grupo<extra></extra>"))
    chart_style(fig, height=250, legend=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(tickfont={"size": 11})
    return fig


def group_distribution(stats: pd.DataFrame) -> go.Figure:
    labels = [f"{g} · {'1.ª' if p.startswith('Antes') else '2.ª'}" for g, p in zip(stats.pasarela, stats.mitad, strict=True)]
    fig = go.Figure()
    for cluster in range(3):
        values = stats[f"porcentaje_grupo_{cluster}"]
        fig.add_trace(go.Bar(x=values, y=labels, name=f"Grupo {cluster}", orientation="h",
                            marker_color=CLUSTER_COLORS[str(cluster)], texttemplate="%{x:.1f} %", textposition="inside",
                            insidetextfont={"color": "white", "size": 12}, customdata=stats.minutos.to_numpy(),
                            hovertemplate="%{y}<br>%{x:.2f} % · %{customdata} resúmenes<extra>%{fullData.name}</extra>"))
    chart_style(fig, height=280)
    fig.update_layout(barmode="stack", bargap=.36, uniformtext={"minsize": 11, "mode": "hide"})
    fig.update_xaxes(range=[0, 100], ticksuffix=" %", showgrid=True, gridcolor="#e9eef5", title=None)
    fig.update_yaxes(autorange="reversed", showgrid=False, title=None)
    return fig


def before_after(stats: pd.DataFrame, metric: str, unit: str) -> go.Figure:
    fig = go.Figure()
    for gateway in GATEWAYS:
        subset = stats[stats.pasarela == gateway]
        fig.add_trace(go.Bar(x=subset.mitad.map(PERIOD_NAMES), y=subset[metric], name=gateway,
                            marker={"color": GATEWAY_COLORS[gateway], "cornerradius": 3},
                            texttemplate="%{y:.2f}", textposition="outside", cliponaxis=False,
                            hovertemplate=f"%{{x}}<br>%{{y:.3f}} {unit}<extra>{gateway}</extra>"))
    chart_style(fig, height=300)
    fig.update_layout(barmode="group", bargap=.38, bargroupgap=.08, yaxis_title=unit)
    fig.update_yaxes(range=[0, max(float(stats[metric].max())*1.24, 1)])
    return fig
