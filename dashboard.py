"""Tres vistas de Streamlit; las estadísticas se comparten con la defensa."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline import StreamingExperiment
    from review import ReviewedRun

from config import GATEWAYS, PROFILES
from bi_metrics import evolution_by_gateway, gateway_kpis
from report import cluster_characterization, comparison_table, interpretation, metric_changes, morris_metrics

GATEWAY_COLORS = {"Ámbar": "#D59A24", "Cobalto": "#2584D4"}
CLUSTER_COLORS = {"0": "#D59A24", "1": "#2584D4", "2": "#9270D2"}
LABELS = {"pasarela": "Pasarela", "mitad": "Periodo", "minutos": "Resúmenes", "cluster": "Grupo",
          "eventos": "Resúmenes", "accesos_medios": "Accesos correctos/min", "fallos_medios": "Fallos/min",
          "cuentas_medias": "Cuentas/min", "ips_medias": "IP/min", "interpretacion": "Contraste observado",
          "fallos_totales": "Fallos totales", "pct_perfil_repartido": "Perfil repartido (%)",
          **{f"porcentaje_grupo_{i}": f"Grupo {i} (%)" for i in range(3)},
          **{f"porcentaje_{p}": f"{p.replace('_', ' ').capitalize()} (%)" for p in PROFILES}}


def _style_figure(fig: go.Figure, *, height: int = 350) -> go.Figure:
    """Tema Plotly coherente con el lienzo BI sin alterar los datos."""
    fig.update_layout(
        template="plotly_white", height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#293f58", "size": 12},
        hoverlabel={"bgcolor": "#183752", "font_color": "white", "font_size": 12},
        margin={"l": 20, "r": 20, "t": 25, "b": 20},
        legend={"orientation": "h", "y": 1.12, "x": 0, "title_text": "", "font_size": 11},
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#d8e2ec", tickfont_color="#718298")
    fig.update_yaxes(gridcolor="#e9eff5", zeroline=False, tickfont_color="#718298")
    return fig


def _section(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="bi-section"><h2>{title}</h2><span>{subtitle}</span></div>',
                unsafe_allow_html=True)


def filter_points(points: pd.DataFrame, gateway: str, period: str, groups: list[int]) -> pd.DataFrame:
    selected = points[points.cluster.isin(groups)]
    if gateway != "Ambas":
        selected = selected[selected.pasarela == gateway]
    if period != "Completo":
        selected = selected[selected.id.le(3000) if period == "Primera mitad" else selected.id.gt(3000)]
    return selected.copy()


def group_distribution(stats: pd.DataFrame, key: str) -> None:
    table = stats.copy()
    table["Periodo / pasarela"] = table.pasarela + " · " + table.mitad
    long = table.melt(id_vars="Periodo / pasarela", value_vars=[f"porcentaje_grupo_{i}" for i in range(3)],
                      var_name="Grupo", value_name="Frecuencia (%)")
    long["Grupo"] = long.Grupo.str.removeprefix("porcentaje_grupo_")
    fig = px.bar(long, x="Periodo / pasarela", y="Frecuencia (%)", color="Grupo",
                 color_discrete_map=CLUSTER_COLORS, category_orders={"Grupo": ["0", "1", "2"]},
                 barmode="stack", range_y=[0, 100])
    st.plotly_chart(_style_figure(fig, height=330), width="stretch", key=key)


def render_detection(exp: StreamingExperiment | ReviewedRun) -> None:
    with st.expander("Detección de cambios de comportamiento", expanded=False):
        detector = exp.detector
        cfg = detector.config
        st.caption(f"Media móvil: {cfg.window} resúmenes/pasarela. Referencia: primeros {cfg.baseline_events}. "
                   f"Evaluación cada {cfg.stride} minutos; persistencia: {cfg.persistence} ventanas. "
                   "Sin datos futuros ni conocimiento del instante del cambio.")
        found = detector.first_detection
        if found:
            st.warning(f"Cambio observado · Primera detección en ID {found['id']} · {found['instante']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Cobalto en la detección", f"{found['cuentas_Cobalto']:.2f} cuentas/min")
            c2.metric("Aumento sobre referencia", f"{found['aumento_cobalto']:+.2f} cuentas/min")
            c3.metric("Aumento frente a Ámbar", f"{found['diferencia_control']:+.2f} cuentas/min")
        elif len(detector.baseline) < 2:
            st.info("Construyendo la referencia inicial con los datos recibidos.")
        else:
            st.success("Estado normal: no se ha observado un cambio persistente según el criterio configurado.")
        history = pd.DataFrame(detector.history)
        if not history.empty:
            for metric, title in (("cuentas", "Cuentas distintas/min · media móvil"), ("fallos", "Fallos/min · media móvil")):
                fig = go.Figure()
                for gateway in GATEWAYS:
                    fig.add_trace(go.Scatter(x=history.instante, y=history[f"{metric}_{gateway}"],
                                             name=gateway, line={"color": GATEWAY_COLORS[gateway]}))
                if metric == "cuentas" and len(detector.baseline) == 2:
                    for gateway in GATEWAYS:
                        # La referencia solo se muestra a partir de su observación completa.
                        part = history[history.minuto >= cfg.baseline_events]
                        fig.add_trace(go.Scatter(x=part.instante, y=[detector.baseline[gateway]]*len(part),
                                                 name=f"Referencia {gateway}", line={"color": GATEWAY_COLORS[gateway], "dash": "dot"}))
                if found:
                    fig.add_shape(type="line", x0=found["instante"], x1=found["instante"], y0=0, y1=1,
                                  yref="paper", line={"color": "#b05e62", "dash": "dash"})
                fig.update_layout(yaxis_title=title, xaxis_title="Instante simulado")
                st.plotly_chart(_style_figure(fig, height=290), width="stretch", key=f"change_{metric}")
        st.caption(f"Criterio: aumento Cobalto ≥ max({cfg.min_increase:g} cuentas/min, "
                   f"{100*cfg.relative_increase:g} % de su referencia) y aumento diferencial frente a Ámbar "
                   f"≥ {cfg.min_control_gap:g} cuentas/min. Las ventanas se solapan; esta heurística exploratoria "
                   "no garantiza detección perfecta ni acredita un incidente.")


def render_dashboard(exp: StreamingExperiment | ReviewedRun) -> None:
    """Panel estilo Power BI: las tres vistas oficiales comparten datos y modelos."""
    n = exp.event_count
    status = "EJECUCIÓN COMPLETA" if exp.is_finished else "SIMULACIÓN EN CURSO"
    st.markdown(
        f'<div class="bi-hero"><div><div class="bi-eyebrow">BIG DATA / SECURITY ANALYTICS / INFORME EN DIRECTO</div>'
        f'<h1>Observatorio de autenticación</h1>'
        f'<p>Dos pasarelas · 3 patrones · Morris × 8 · UMAP 2D · K-means k=3</p></div>'
        f'<div class="bi-pill">● {status}</div></div>',
        unsafe_allow_html=True,
    )
    st.progress(n / 6000, text=f"{n:,} / 6.000 eventos procesados · {n//2:,} minutos simulados")
    if n < 300:
        st.info("El mapa y las tres vistas se activarán en el evento 300. Después se actualizarán en 400, 500, …, 6000.")
        return

    raw, points = exp.from_csv(), exp.snapshot()
    counts = gateway_kpis(raw)
    last_time = str(points.iloc[-1].instante).replace("T", " · ")
    st.caption(f"Último ID: {n} · Instante simulado: {points.iloc[-1].instante}")

    # KPI superiores: información recibida hasta este instante, no valores futuros.
    kpi = st.columns(4)
    kpi[0].metric("Eventos procesados", f"{n:,}", help="Resúmenes recibidos de ambas pasarelas.")
    kpi[1].metric("Fallos totales · exactos", f"{sum(int(v['fallos']) for v in counts.values()):,}",
                  help="Suma real de los fallos recibidos en ambos CSV.")
    kpi[2].metric("Cuentas/min · Cobalto", f"{counts['Cobalto']['cuentas_medias']:.2f}",
                  help="Media por minuto de las cuentas distintas implicadas en los fallos.")
    kpi[3].metric("Cobertura ML", f"{len(points):,} puntos", help="Eventos proyectados y asignados a K-means.")

    if exp.is_finished:
        stats = comparison_table(points)
        before = stats[(stats.pasarela == "Cobalto") & (stats.mitad.str.startswith("Antes"))].iloc[0]
        after = stats[(stats.pasarela == "Cobalto") & (stats.mitad.str.startswith("Después"))].iloc[0]
        change = float(after.cuentas_medias - before.cuentas_medias)
        diff_failures = float(after.fallos_medios - before.fallos_medios)
        st.markdown(
            '<div class="bi-callout">'
            f'<strong>HALLAZGO PRINCIPAL · Cobalto: {before.cuentas_medias:.3f} → '
            f'{after.cuentas_medias:.3f} cuentas/min ({change:+.3f})</strong>'
            f'<span class="bi-desc">Los fallos apenas varían ({diff_failures:+.3f} fallos/min). '
            'Ámbar actúa como control: el cambio importante está en la distribución de los fallos, '
            'no en su volumen. Cifras observadas sobre 1.500 minutos por mitad.</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="bi-callout"><strong>MONITORIZACIÓN INCREMENTAL</strong>'
            '<span class="bi-desc">Los indicadores utilizan exclusivamente los eventos recibidos. '
            'La comparación definitiva entre mitades estará disponible al completar 6.000 eventos.</span></div>',
            unsafe_allow_html=True,
        )

    tab1, tab2, tab3 = st.tabs([
        "01 · Fallos por pasarela", "02 · Mapa UMAP y grupos", "03 · Antes y después",
    ])

    with tab1:
        _section("Precisión de Morris", "Valor estimado vs. recuento exacto de los CSV")
        st.caption("Un resumen puede representar decenas de intentos fallidos. Morris cuenta intentos, no filas.")
        for gateway, column in zip(GATEWAYS, st.columns(2), strict=True):
            with column, st.container(border=True):
                st.markdown(f"**{'🟡' if gateway == 'Ámbar' else '🔵'} Pasarela {gateway}**")
                exact = int(counts[gateway]["fallos"])
                metrics = morris_metrics(exact, exp.morris.estimate(gateway))
                left, right = st.columns(2)
                left.metric("Fallos exactos", f"{exact:,}",
                            help="Suma de la columna fallos del CSV de esta pasarela.")
                right.metric("Estimación Morris", f"{metrics['estimacion_morris']:,.1f}",
                             delta=f"{metrics['diferencia_con_signo']:+,.1f}", delta_color="off",
                             help="Media de ocho estimaciones 2^c−1; delta = estimado − exacto.")
                st.caption(f"Error absoluto: **{metrics['error_absoluto']:,.1f} intentos** · "
                           f"Error relativo: **{metrics['error_relativo_porcentaje']:.2f} %**")
                st.caption(f"Registros c₁…c₈: {exp.morris.counters[gateway].registers}")

        _section("Evolución de fallos acumulados", "Morris frente al total exacto")
        history = pd.DataFrame(exp.history)
        with st.container(border=True):
            trend = go.Figure()
            for gateway in GATEWAYS:
                for prefix, label, dash in (("real", "Exacto", "solid"), ("morris", "Morris", "dot")):
                    trend.add_trace(go.Scatter(
                        x=history.instante, y=history[f"{prefix}_{gateway}"],
                        name=f"{gateway} · {label}", mode="lines",
                        line={"color": GATEWAY_COLORS[gateway], "dash": dash, "width": 2.6},
                        hovertemplate="%{x}<br>%{y:,.0f} intentos<extra>%{fullData.name}</extra>",
                    ))
            trend.update_layout(yaxis_title="Intentos fallidos acumulados", xaxis_title="Instante simulado")
            st.plotly_chart(_style_figure(trend, height=365), width="stretch", key="morris_chart")

        _section("Calidad de estimación", "Evolución del error relativo absoluto")
        with st.container(border=True):
            errors = go.Figure()
            for gateway in GATEWAYS:
                exact = history[f"real_{gateway}"]
                relative = 100 * (history[f"morris_{gateway}"] - exact).abs().div(exact.where(exact.ne(0))).fillna(0)
                errors.add_trace(go.Scatter(x=history.instante, y=relative, name=gateway, mode="lines",
                                            line={"color": GATEWAY_COLORS[gateway], "width": 2.7},
                                            hovertemplate="%{x}<br>%{y:.2f} %<extra>%{fullData.name}</extra>"))
            errors.update_layout(yaxis_title="Error relativo absoluto (%)", xaxis_title="Instante simulado")
            st.plotly_chart(_style_figure(errors, height=275), width="stretch", key="morris_error_chart")
        with st.expander("Auditoría de los 8 registros por pasarela"):
            registers = pd.DataFrame([
                {"Pasarela": g, "Registro": i + 1, "Valor c": c, "Estimación 2^c−1": 2 ** c - 1}
                for g in GATEWAYS for i, c in enumerate(exp.morris.counters[g].registers)
            ])
            st.dataframe(registers, hide_index=True, width="stretch")
            fig = px.bar(registers, x="Registro", y="Estimación 2^c−1", color="Pasarela",
                         barmode="group", color_discrete_map=GATEWAY_COLORS)
            st.plotly_chart(_style_figure(fig, height=290), width="stretch", key="registers_chart")
        st.caption("Morris incrementa con probabilidad 2⁻ᶜ. Las ocho réplicas reducen la variabilidad, "
                   "pero no garantizan exactitud en una realización concreta.")

    with tab2:
        _section("Mapa de actividad", "Embeddings UMAP 2D · 3 centroides entrenados en los primeros 300 eventos")
        f1, f2, f3 = st.columns([1.1, 1.2, 1.4])
        gateway = f1.selectbox("Pasarela", ["Ambas", *GATEWAYS], key="gateway_filter")
        period = f2.selectbox("Periodo", ["Completo", "Primera mitad", "Segunda mitad"], key="period_filter")
        groups = f3.multiselect("Grupos K-means", [0, 1, 2], default=[0, 1, 2], key="group_filter")
        dataset = filter_points(points, gateway, period, groups)
        st.caption(f"{len(dataset):,} puntos seleccionados de {len(points):,}. Los centroides permanecen fijos desde el evento 300.")
        with st.container(border=True):
            dataset["grupo"] = dataset.cluster.astype(str)
            fig = px.scatter(dataset, x="umap_x", y="umap_y", color="grupo", color_discrete_map=CLUSTER_COLORS,
                             category_orders={"grupo": ["0", "1", "2"]},
                             hover_data=["id", "instante", "pasarela", "fallos", "cuentas", "ips_origen", "perfil"],
                             labels={"grupo": "Grupo", "umap_x": "UMAP 1", "umap_y": "UMAP 2", "id": "ID",
                                     "instante": "Minuto", "pasarela": "Pasarela", "fallos": "Fallos/min",
                                     "cuentas": "Cuentas/min", "ips_origen": "IP/min", "perfil": "Perfil generado"},
                             opacity=.7, render_mode="webgl")
            fig.update_traces(marker={"size": 7})
            if exp.centroids is not None:
                for group in groups:
                    center = exp.centroids[group]
                    fig.add_trace(go.Scattergl(
                        x=[center[0]], y=[center[1]], mode="markers+text", name=f"Centroide {group}",
                        text=[f"C{group}"], textposition="top right", textfont={"size": 12, "color": "#17304a"},
                        marker={"symbol": "x", "size": 17, "color": "#142c45", "line": {"width": 2, "color": "white"}},
                        hovertemplate=f"Centroide fijo del grupo {group}<br>UMAP 1: %{{x:.3f}}<br>UMAP 2: %{{y:.3f}}<extra></extra>",
                    ))
            st.plotly_chart(_style_figure(fig, height=485), width="stretch", key="umap_chart")
        if dataset.empty:
            st.info("No hay eventos en la selección actual.")
        else:
            chars, cross = cluster_characterization(dataset)
            _section("Calidad de los grupos", "Perfil simulado usado solo para auditoría posterior")
            left, right = st.columns([1, 1.15])
            with left, st.container(border=True):
                st.markdown("**Caracterización de clústeres**")
                st.dataframe(chars.rename(columns=LABELS).round(3), hide_index=True, width="stretch")
            with right, st.container(border=True):
                st.markdown("**Correspondencia grupo ↔ perfil (%)**")
                heat = px.imshow(cross.rename(columns={p: p.replace("_", " ") for p in PROFILES}),
                                 text_auto=".1f", zmin=0, zmax=100,
                                 color_continuous_scale=[[0, "#edf5fd"], [.5, "#6ba7d8"], [1, "#17508f"]],
                                 labels={"x": "Perfil simulado", "y": "Grupo", "color": "% del grupo"}, aspect="auto")
                heat.update_yaxes(tickmode="array", tickvals=list(cross.index))
                st.plotly_chart(_style_figure(heat, height=315), width="stretch", key="profile_heatmap")
        _section("Frecuencia de grupos", "Comparación acumulada por pasarela y periodo")
        with st.container(border=True):
            group_distribution(comparison_table(points), "map_group_distribution")
        st.caption("Las frecuencias anteriores se calculan sobre todos los eventos observados, sin aplicar los "
                   "filtros del mapa. El perfil generado no interviene en el aprendizaje de UMAP/K-means. "
                   "Las agrupaciones describen patrones, no prueban un ataque real.")

    with tab3:
        _section("Antes y después", "La mitad de cada pasarela corresponde a 1.500 resúmenes")
        # Esta evolución se calcula solo a partir de datos ya emitidos, por bloques de 100 minutos.
        evolution = evolution_by_gateway(raw, minutes_per_bin=100)
        with st.container(border=True):
            st.markdown("**Evolución de cuentas afectadas por minuto**")
            st.markdown('<p class="bi-chart-note">Promedios por bloques de 100 minutos por pasarela. '
                        'La línea discontinua marca el cambio de distribución programado (minuto 1.500).</p>',
                        unsafe_allow_html=True)
            chart = go.Figure()
            for gateway in GATEWAYS:
                sub = evolution.loc[evolution.pasarela == gateway]
                chart.add_trace(go.Scatter(x=sub.minuto_fin, y=sub.cuentas_medias, mode="lines+markers",
                                           name=gateway, line={"color": GATEWAY_COLORS[gateway], "width": 3},
                                           marker={"size": 6},
                                           hovertemplate="Minuto %{x}<br>%{y:.2f} cuentas/min<extra>%{fullData.name}</extra>"))
            if n > 3000:
                chart.add_vline(x=1500, line_width=1.5, line_dash="dash", line_color="#8d9db0",
                                annotation_text="Cambio simulado", annotation_font_color="#586d85")
            chart.update_layout(xaxis_title="Minuto simulado", yaxis_title="Cuentas distintas/min")
            st.plotly_chart(_style_figure(chart, height=345), width="stretch", key="accounts_trend")
        if not exp.is_finished:
            st.info("El análisis final de mitades se muestra tras el evento 6000: cada periodo necesita exactamente "
                    "1.500 resúmenes por pasarela.")
        else:
            stats = comparison_table(points)
            variations = metric_changes(stats)
            accounts = variations[variations.metrica == "cuentas_medias"].set_index("pasarela")
            c1, c2, c3 = st.columns(3)
            c1.metric("Cambio Cobalto · cuentas/min", f"{accounts.loc['Cobalto', 'diferencia']:+.3f}",
                      help="Media de la segunda mitad menos la primera; cuentas distintas por minuto.")
            c2.metric("Cambio Ámbar · cuentas/min", f"{accounts.loc['Ámbar', 'diferencia']:+.3f}")
            c3.metric("Diferencia en diferencias", f"{accounts.loc['Cobalto', 'diferencia'] - accounts.loc['Ámbar', 'diferencia']:+.3f}",
                      help="Cambio en Cobalto menos cambio en Ámbar, medido en cuentas/min.")
            _section("Indicadores por periodo", "Cuentas, fallos e IP medias por minuto")
            for metric, column in zip(("cuentas_medias", "fallos_medios", "ips_medias"), st.columns(3), strict=True):
                with column, st.container(border=True):
                    fig = px.bar(stats, x="pasarela", y=metric, color="mitad", barmode="group",
                                 color_discrete_sequence=["#a9bfd3", "#276c9c"], labels=LABELS)
                    fig.update_layout(title={"text": LABELS[metric], "font_size": 14})
                    st.plotly_chart(_style_figure(fig, height=315), width="stretch", key=f"before_after_{metric}")
            _section("Frecuencia de K-means", "Porcentaje de cada grupo por mitad y pasarela")
            with st.container(border=True):
                group_distribution(stats, "before_after_distribution")
            _section("Detalle auditable", "Medias calculadas sobre los CSV y las 6.000 proyecciones")
            st.dataframe(stats[["pasarela", "mitad", "minutos", "fallos_medios", "cuentas_medias", "ips_medias"]]
                         .rename(columns=LABELS).round(3), hide_index=True, width="stretch")
            variations["metrica"] = variations.metrica.map(LABELS)
            with st.expander("Variaciones y porcentajes de perfiles/grupos", expanded=False):
                st.dataframe(variations.rename(columns={"pasarela": "Pasarela", "metrica": "Medida por minuto",
                                                          "antes": "Antes", "despues": "Después", "diferencia": "Cambio absoluto",
                                                          "variacion_porcentaje": "Variación (%)"}).round(3),
                             hide_index=True, width="stretch")
                st.dataframe(stats[["pasarela", "mitad", *[f"porcentaje_grupo_{i}" for i in range(3)],
                                    *[f"porcentaje_{p}" for p in PROFILES]]].rename(columns=LABELS).round(2),
                             hide_index=True, width="stretch")
            st.markdown(f'<div class="bi-callout"><strong>INTERPRETACIÓN DEL EXPERIMENTO</strong>'
                        f'<span class="bi-desc">{interpretation(stats)}</span></div>', unsafe_allow_html=True)
        render_detection(exp)

    if exp.is_finished:
        st.success("Ejecución completa: 6.000 eventos y resultados exportados. Descarga los ficheros de la defensa.")
        for column, (label, path, mime) in zip(st.columns(3), (
            ("CSV Ámbar", exp.paths.data / "ambar.csv", "text/csv"),
            ("CSV Cobalto", exp.paths.data / "cobalto.csv", "text/csv"),
            ("Informe de defensa · PDF", exp.paths.results / "Informe_Defensa_Tecnica.pdf", "application/pdf"),
        ), strict=True):
            column.download_button(label, path.read_bytes(), file_name=path.name, mime=mime)
