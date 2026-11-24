"""Tres vistas de análisis. La presentación consume las mismas cifras que la defensa."""
from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING, TypeAlias

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import bi_charts as charts
from bi_metrics import DashboardData, PERIOD_NAMES, PROFILE_NAMES, build_dashboard_data, filter_points, number
from config import GATEWAYS, PROFILES
from report import cluster_characterization, morris_metrics
from ui_theme import CLUSTER_COLORS, GATEWAY_COLORS, chart_style, insight, plot

if TYPE_CHECKING:
    from pipeline import StreamingExperiment
    from review import ReviewedRun

Run: TypeAlias = "StreamingExperiment | ReviewedRun"
TABS = ["Fallos y Morris", "Mapa UMAP y grupos", "Antes y después"]
LABELS = {"pasarela": "Pasarela", "mitad": "Periodo", "minutos": "Resúmenes", "cluster": "Grupo",
          "eventos": "Resúmenes", "accesos_medios": "Correctos/min", "fallos_medios": "Fallos/min",
          "cuentas_medias": "Cuentas/min", "ips_medias": "IP/min", "interpretacion": "Predominio observado"}


def _data(exp: Run) -> DashboardData:
    # Los filtros no vuelven a leer los CSV ni a recalcular agregados completos.
    # Un nuevo lote, una nueva simulación o una recarga de revisión invalidan la copia.
    token = (id(exp), str(exp.output_dir), exp.event_count)
    cached = st.session_state.get("dashboard_snapshot")
    if cached is None or cached[0] != token:
        cached = (token, build_dashboard_data(exp.from_csv(), exp.snapshot()))
        st.session_state.dashboard_snapshot = cached
    return cached[1]


def _table(frame: pd.DataFrame, *, decimals: int = 2, key: str | None = None) -> None:
    """Formato español con valores numéricos preservados para ordenar/exportar."""
    data = frame.rename(columns=LABELS).copy()
    if "Periodo" in data:
        data["Periodo"] = data.Periodo.replace(PERIOD_NAMES)
    numeric = data.select_dtypes(include="number").columns
    formats = {col: (lambda x, d=0 if col in ("Grupo", "Resúmenes", "Registro", "Valor c") else decimals: number(x, d)) for col in numeric}
    st.dataframe(data.style.format(formats), hide_index=True, width="stretch", key=key)


def render_overview(data: DashboardData) -> None:
    if data.comparison_ready:
        accounts = data.change("Cobalto", "cuentas_medias")
        failures = data.change("Cobalto", "fallos_medios")
        metrics = [
            ("summary_cobalto", "Cuentas en Cobalto", number(accounts.after, 2), f"{number(accounts.percentage, 1, signed=True)} %",
             f"Antes: {number(accounts.before, 2)} · cuentas/min", "Media de cuentas distintas afectadas por minuto en la segunda mitad; variación frente a la primera."),
            ("summary_fallos", "Fallos en Cobalto", number(failures.after, 2), f"{number(failures.percentage, 2, signed=True)} %",
             f"Antes: {number(failures.before, 2)} · fallos/min", "Media de fallos por minuto. Cada periodo contiene 1.500 resúmenes de Cobalto."),
            ("summary_control", "Cambio frente a Ámbar", number(data.accounts_did, 3, signed=True), None,
             "Cuentas/min · diferencia en diferencias", "Cambio de cuentas en Cobalto menos el cambio de cuentas en Ámbar, que conserva su distribución."),
            ("summary_events", "Eventos analizados", number(len(data.points)), None,
             "3.000 por pasarela · 3 grupos", "Cada evento es un resumen por minuto y pasarela; hay dos resúmenes por minuto simulado."),
        ]
        title = "El cambio se hace visible al observar las cuentas"
        insight(title, f"Cobalto cambia {number(accounts.difference, 3, signed=True)} cuentas/min "
                f"({number(accounts.percentage, 2, signed=True)} %), frente a {number(failures.difference, 3, signed=True)} fallos/min. "
                "Comparar volumen y alcance permite interpretar el comportamiento.")
    else:
        metrics = [
            ("summary_ambar", "Resúmenes de Ámbar", number(data.raw.pasarela.eq("Ámbar").sum()), None, "Pasarela de referencia", "Una fila por minuto; ID impares."),
            ("summary_cobalto", "Resúmenes de Cobalto", number(data.raw.pasarela.eq("Cobalto").sum()), None, "Pasarela bajo observación", "Una fila por minuto; ID pares."),
            ("summary_fallos", "Fallos exactos totales", number(data.raw.fallos.sum()), None, "Intentos · suma de ambos CSV", "Total de intentos fallidos, no número de resúmenes."),
            ("summary_events", "Puntos proyectados", number(data.points.cluster.notna().sum()), None, "UMAP 2D · ajuste inicial conservado", "300 eventos iniciales y transformación posterior sin reentrenar."),
        ]
    for column, (key, label, value, delta, caption, help_text) in zip(st.columns(4), metrics, strict=True):
        with column, st.container(border=True, key=key):
            st.metric(label, value, delta=delta, delta_color="off", help=help_text)
            st.caption(caption)


def render_morris(exp: Run, data: DashboardData) -> None:
    st.subheader("¿Cuántos intentos fallidos se han recibido?")
    st.caption("El CSV da el total exacto. Morris lo aproxima con ocho registros por pasarela; cada resumen puede contener muchos fallos.")
    for gateway, column in zip(GATEWAYS, st.columns(2), strict=True):
        with column, st.container(border=True, key=f"panel_morris_{gateway}"):
            st.markdown(f'<span class="legend-pill" style="color:{GATEWAY_COLORS[gateway]};background:{GATEWAY_COLORS[gateway]}12">{gateway}</span>', unsafe_allow_html=True)
            exact = int(data.raw.loc[data.raw.pasarela == gateway, "fallos"].sum())
            m = morris_metrics(exact, exp.morris.estimate(gateway))
            left, right = st.columns(2)
            left.metric("Fallos exactos", number(exact), help="Suma de fallos del CSV de esta pasarela, en intentos.")
            right.metric("Estimación Morris", number(m["estimacion_morris"]),
                         delta=f"{number(m['diferencia_con_signo'], signed=True)} vs. CSV", delta_color="off",
                         help="Media de ocho estimaciones 2^c−1; diferencia con signo = estimación menos exacto.")
            st.caption(f"Error absoluto: {number(m['error_absoluto'])} intentos · Error relativo: {number(m['error_relativo_porcentaje'], 2)} %")
    left, right = st.columns([1.55, 1])
    history = pd.DataFrame(exp.history)
    with left, st.container(border=True, key="panel_volume"):
        st.subheader("Volumen acumulado")
        st.caption("Línea continua: CSV exacto · punteada: estimación Morris")
        plot(charts.morris_evolution(history), "morris_chart")
    with right, st.container(border=True, key="panel_precision"):
        st.subheader("Precisión de la estimación")
        st.caption("Menor porcentaje significa menor error respecto al CSV.")
        plot(charts.morris_error(history), "morris_error_chart")
    with st.expander("Cómo funciona Morris · inspeccionar los ocho registros"):
        st.write("Cada intento fallido produce un sorteo independiente por registro. Si **u < 2⁻ᶜ**, "
                 "el registro aumenta. La media de **ocho estimaciones 2ᶜ − 1** reduce la varianza, pero no elimina el error aleatorio.")
        rows = [{"Pasarela": g, "Registro": i+1, "Valor c": c, "Estimación individual": 2**c-1}
                for g in GATEWAYS for i, c in enumerate(exp.morris.counters[g].registers)]
        registers = pd.DataFrame(rows)
        a, b = st.columns([1, 1.3])
        with a:
            _table(registers, decimals=0)
        with b:
            fig = px.bar(registers, x="Registro", y="Estimación individual", color="Pasarela", barmode="group", color_discrete_map=GATEWAY_COLORS)
            plot(chart_style(fig, height=360), "registers_chart")


def _reset_filters() -> None:
    st.session_state.gateway_filter = "Ambas"
    st.session_state.period_filter = "Completo"
    st.session_state.group_filter = [0, 1, 2]
    st.session_state.resetting_map_filters = True


def render_map(exp: Run, data: DashboardData) -> None:
    st.subheader("¿Qué patrones de actividad aparecen?")
    st.caption("Cada punto es un resumen. El color identifica su grupo K-means; las cruces C0, C1 y C2 son los centroides fijos.")
    with st.container(border=True):
        a, b, c, d = st.columns([1, 1, 1.3, .7], vertical_alignment="bottom")
        gateway = a.selectbox("Pasarela", ["Ambas", *GATEWAYS], key="gateway_filter")
        period = b.selectbox("Periodo", ["Completo", "Primera mitad", "Segunda mitad"], key="period_filter")
        # El valor inicial explícito también se conserva al remontar el widget
        # tras cambiar de modo. En el callback la selección ya viene del estado.
        resetting = st.session_state.pop("resetting_map_filters", False)
        groups = c.multiselect("Grupos K-means", [0, 1, 2], default=None if resetting else [0, 1, 2], key="group_filter")
        d.button("Restablecer", key="reset_filters", on_click=_reset_filters, width="stretch", help="Mostrar ambas pasarelas, todo el periodo y los tres grupos.")
        selected = filter_points(data.points, gateway, period, groups)
        trained = int(selected.id.le(300).sum())
        st.caption(f"{number(len(selected))} puntos seleccionados de {number(len(data.points))} · "
                   f"{number(trained)} de ajuste inicial · {number(len(selected)-trained)} transformados después")
    main, aside = st.columns([2.1, 1])
    with main, st.container(border=True, key="panel_map"):
        plot(charts.umap_map(selected, data.points, exp.centroids, groups), "umap_chart")
        st.caption("UMAP 1 y 2 no tienen unidades físicas. Los límites del plano se conservan al filtrar; los modelos no se vuelven a entrenar.")
    with aside:
        st.subheader("Lectura de la selección")
        if selected.empty:
            st.info("No hay eventos en la selección actual. Amplía los filtros o pulsa Restablecer.")
            chars, cross = pd.DataFrame(), pd.DataFrame()
        else:
            chars, cross = cluster_characterization(selected)
            for row in chars.itertuples():
                majority = cross.loc[row.cluster].idxmax()
                st.markdown(f'<div class="group-card" style="--group:{CLUSTER_COLORS[str(row.cluster)]}">'
                            f'<div class="group-name">Grupo {row.cluster} · {number(row.eventos)} resúmenes</div>'
                            f'<div class="group-value">{number(row.cuentas_medias, 2)} <span style="font-size:.85rem;font-weight:400">cuentas/min</span></div>'
                            f'<div class="group-body">{number(row.fallos_medios, 2)} fallos/min · {number(row.ips_medias, 2)} IP/min<br>'
                            f'{escape(PROFILE_NAMES[majority])}: {number(float(cross.loc[row.cluster].max()), 1)} % del grupo</div></div>', unsafe_allow_html=True)
            st.caption("Descripción calculada después de agrupar. Los ID de grupo no tienen un significado prefijado.")
    a, b = st.columns(2)
    with a, st.container(border=True, key="panel_profiles"):
        st.subheader("¿Coinciden grupos y perfiles?")
        st.caption("Selección actual · porcentaje de cada perfil dentro de su grupo")
        if not cross.empty:
            plot(charts.profile_heatmap(cross), "profile_heatmap")
        else:
            st.info("Selecciona puntos para contrastar los perfiles.")
    with b, st.container(border=True, key="panel_distribution"):
        st.subheader("Distribución de los grupos")
        st.caption("Todos los eventos recibidos · 1.ª y 2.ª mitad por pasarela")
        plot(charts.group_distribution(data.periods), "map_group_distribution")
        if not data.comparison_ready:
            st.caption("Frecuencias provisionales: los periodos todavía no están completos.")
    with st.expander("Medias por grupo y protocolo de entrenamiento"):
        if not chars.empty:
            _table(chars.drop(columns="interpretacion"), decimals=3)
        st.write("**4 medidas → StandardScaler → UMAP 2D → K-means (k=3).** Los ID 1–300 "
                 "(150 por pasarela) ajustan los tres modelos una sola vez. Los siguientes usan transform y predict. "
                 "ID, instante, pasarela y perfil quedan fuera del vector de aprendizaje.")
    st.caption("El perfil simulado sirve solo para auditoría posterior. Un grupo describe patrones de acceso; por sí solo no demuestra un ataque real.")


def render_detection(exp: Run) -> None:
    with st.expander("Detección de cambios de comportamiento · análisis exploratorio"):
        detector, cfg = exp.detector, exp.detector.config
        found = detector.first_detection
        st.caption(f"Media móvil de {cfg.window} resúmenes por pasarela · referencia: primeros {cfg.baseline_events} observados · evaluación cada {cfg.stride} minutos")
        if found:
            st.warning(f"Cambio observado · Primera detección en ID {found['id']} · {found['instante']}")
            a, b, c = st.columns(3)
            a.metric("Cobalto en la detección", number(found["cuentas_Cobalto"], 2), help="Cuentas distintas/min en la ventana de detección.")
            b.metric("Aumento sobre referencia", number(found["aumento_cobalto"], 2, signed=True))
            c.metric("Aumento frente a Ámbar", number(found["diferencia_control"], 2, signed=True))
        elif len(detector.baseline) < 2:
            st.info("Construyendo la referencia con datos ya observados.")
        else:
            st.info("Estado normal según el criterio configurado: no se ha observado un cambio persistente.")
        history = pd.DataFrame(detector.history)
        if not history.empty:
            for column, metric, unit in zip(st.columns(2), ("cuentas", "fallos"), ("Cuentas distintas/min", "Fallos/min"), strict=True):
                with column:
                    fig = go.Figure()
                    for gateway in GATEWAYS:
                        fig.add_trace(go.Scatter(x=history.instante, y=history[f"{metric}_{gateway}"], name=gateway,
                                                 line={"color": GATEWAY_COLORS[gateway], "width": 2}))
                        if metric == "cuentas" and gateway in detector.baseline:
                            part = history[history.minuto >= cfg.baseline_events]
                            fig.add_trace(go.Scatter(x=part.instante, y=[detector.baseline[gateway]]*len(part),
                                                     name=f"Referencia {gateway}", line={"color": GATEWAY_COLORS[gateway], "dash": "dot"}))
                    if found:
                        fig.add_shape(type="line", x0=found["instante"], x1=found["instante"], y0=0, y1=1, yref="paper", line={"color": "#C45074", "dash": "dash"})
                    chart_style(fig, height=320)
                    fig.update_layout(yaxis_title=unit, hovermode="x unified")
                    fig.update_xaxes(type="date", tickformat="%d/%m\n%H:%M", nticks=4)
                    plot(fig, f"change_{metric}")
        st.caption(f"Criterio: aumento Cobalto ≥ max({number(cfg.min_increase, 1)} cuentas/min, "
                   f"{number(100*cfg.relative_increase)} % de su referencia), y aumento diferencial frente a Ámbar "
                   f"≥ {number(cfg.min_control_gap, 1)} cuentas/min durante {cfg.persistence} ventanas consecutivas. "
                   "No utiliza datos futuros ni conoce el evento del cambio. Las ventanas se solapan; esta heurística no prueba un incidente.")


def render_comparison(exp: Run, data: DashboardData) -> None:
    st.subheader("¿Cambió el volumen o cambió el alcance?")
    if not data.comparison_ready:
        st.info("La comparación final estará disponible al completar 6.000 eventos: requiere exactamente 1.500 resúmenes por pasarela y mitad.")
        render_detection(exp)
        return
    st.caption("Primera mitad: ID 1–3.000 · segunda mitad: ID 3.001–6.000 · 1.500 resúmenes en cada barra")
    for column, metric, title, caption, unit in zip(st.columns(2), ("cuentas_medias", "fallos_medios"),
            ("El alcance sobre las cuentas", "El volumen de intentos fallidos"),
            ("Cuentas distintas afectadas por minuto", "Mismo rango de fallos en los dos perfiles de muchos fallos"),
            ("Cuentas/min", "Fallos/min"), strict=True):
        with column, st.container(border=True, key=f"panel_comparison_{metric}"):
            st.subheader(title)
            st.caption(caption)
            plot(charts.before_after(data.periods, metric, unit), f"before_after_{metric}")
    c, a = data.change("Cobalto", "cuentas_medias"), data.change("Ámbar", "cuentas_medias")
    f, af = data.change("Cobalto", "fallos_medios"), data.change("Ámbar", "fallos_medios")
    left, right = st.columns([1, 1.7])
    with left, st.container(border=True, key="panel_did"):
        st.metric("Diferencia en diferencias · cuentas/min", number(data.accounts_did, 3, signed=True),
                  help="(Cobalto después − antes) − (Ámbar después − antes). Comparación descriptiva del experimento.")
        st.caption(f"Cambio Cobalto: {number(c.difference, 3, signed=True)}\n\nCambio Ámbar: {number(a.difference, 3, signed=True)}")
    with right, st.container(border=True, key="panel_conclusion"):
        st.subheader("Conclusión para la defensa")
        st.write(f"**Cobalto pasa de {number(c.before, 3)} a {number(c.after, 3)} cuentas/min** "
                 f"({number(c.percentage, 2, signed=True)} %). Ámbar pasa de {number(a.before, 3)} a {number(a.after, 3)}.")
        st.write(f"Los fallos cambian {number(f.difference, 3, signed=True)}/min en Cobalto y "
                 f"{number(af.difference, 3, signed=True)}/min en Ámbar. El diseño mantiene la esperanza de fallos "
                 "en 32,8/min; observar solo ese volumen no identifica el cambio de alcance.")
        st.caption("Cuentas distintas por minuto ≠ cuentas únicas de toda la simulación. Los resultados describen datos sintéticos.")
    with st.container(border=True, key="panel_evidence"):
        st.subheader("De los patrones a la evidencia")
        st.caption("Frecuencia de cada grupo · porcentajes calculados sobre 1.500 resúmenes")
        plot(charts.group_distribution(data.periods), "before_after_distribution")
        x, y = st.columns(2)
        for column, columns, title in ((x, [f"porcentaje_grupo_{i}" for i in range(3)], "Grupos detectados (%)"),
                                      (y, [f"porcentaje_{p}" for p in PROFILES], "Perfiles simulados (%)")):
            with column:
                st.markdown(f"**{title}**")
                names = {f"porcentaje_grupo_{i}": f"Grupo {i}" for i in range(3)} | {f"porcentaje_{p}": PROFILE_NAMES[p] for p in PROFILES}
                _table(data.periods[["pasarela", "mitad", *columns]].rename(columns=names))
    with st.expander("Detalle numérico · medias, variaciones e IP de origen"):
        _table(data.periods[["pasarela", "mitad", "minutos", "fallos_medios", "cuentas_medias", "ips_medias"]], decimals=3)
        changes = data.changes.copy()
        changes["metrica"] = changes.metrica.map(LABELS)
        _table(changes.rename(columns={"metrica": "Medida por minuto", "antes": "Antes", "despues": "Después", "diferencia": "Cambio absoluto", "variacion_porcentaje": "Variación (%)"}), decimals=3)
        plot(charts.before_after(data.periods, "ips_medias", "IP distintas/min"), "before_after_ips_medias")
    render_detection(exp)


def render_evidence(exp: Run, data: DashboardData) -> None:
    with st.expander("Guía de defensa · los cinco criterios del enunciado"):
        st.caption("Evidencias de esta ejecución; cada criterio tiene una puntuación máxima de 2 puntos. Esta guía no asigna una calificación.")
        ml_ready = exp.ml_real and len(data.points) >= 300
        rows = [
            {"Criterio (máx. 2 puntos)": "Generación y almacenamiento", "Evidencia disponible": f"{number(len(data.raw))} filas; Ámbar {number(data.raw.pasarela.eq('Ámbar').sum())}, Cobalto {number(data.raw.pasarela.eq('Cobalto').sum())}", "Dónde mostrarlo": "CSV descargables y progreso"},
            {"Criterio (máx. 2 puntos)": "Morris y contraste exacto", "Evidencia disponible": "8 registros por pasarela; errores frente a la suma CSV", "Dónde mostrarlo": "Fallos y Morris"},
            {"Criterio (máx. 2 puntos)": "UMAP: proyección de nuevos eventos", "Evidencia disponible": f"300 de ajuste + {number(max(0, len(data.points)-300))} transformados" if ml_ready else "Modelo real pendiente de validación", "Dónde mostrarlo": "Mapa, tooltip y metadatos"},
            {"Criterio (máx. 2 puntos)": "K-means e interpretación", "Evidencia disponible": "3 centroides fijos; medias y contraste con perfiles" if ml_ready else "Modelo real pendiente de validación", "Dónde mostrarlo": "Mapa UMAP y grupos"},
            {"Criterio (máx. 2 puntos)": "Dashboard y defensa con cifras", "Evidencia disponible": "4 periodos de 1.500; comparación final e informe" if data.comparison_ready else "Comparación final pendiente", "Dónde mostrarlo": "Antes y después · PDF"},
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if exp.is_finished:
        with st.container(border=True):
            st.subheader("Evidencia descargable")
            st.caption("Ejecución completa: 6.000 eventos, proyección y resultados exportados.")
            files = [("CSV Ámbar", exp.paths.data / "ambar.csv", "text/csv"),
                     ("CSV Cobalto", exp.paths.data / "cobalto.csv", "text/csv"),
                     ("Informe PDF", exp.paths.results / "Informe_Defensa_Tecnica.pdf", "application/pdf")]
            for column, (label, path, mime) in zip(st.columns(3), files, strict=True):
                column.download_button(label, path.read_bytes(), file_name=path.name, mime=mime, width="stretch")


def render_dashboard(exp: Run) -> None:
    n = exp.event_count
    st.progress(n/6000, text=f"{number(n)} / 6.000 eventos · {number(n//2)} minutos simulados")
    if n < 300:
        st.info("Primera visualización en el evento 300; después, actualizaciones en 400, 500, …, 6000.")
        return
    data = _data(exp)
    instant = pd.Timestamp(data.points.iloc[-1].instante).strftime("%d/%m/%Y %H:%M")
    st.caption(f"Último ID: {n} · Instante simulado: {instant} · Datos de la ejecución actual")
    render_overview(data)
    first, second, third = st.tabs(TABS)
    with first:
        render_morris(exp, data)
    with second:
        render_map(exp, data)
    with third:
        render_comparison(exp, data)
    render_evidence(exp, data)
