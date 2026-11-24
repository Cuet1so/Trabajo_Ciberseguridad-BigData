"""Aplicación local. Arranque: python -m streamlit run app.py [-- --review .]."""
from __future__ import annotations

import argparse
from pathlib import Path
from time import monotonic
from uuid import uuid4

import streamlit as st

from dashboard import render_dashboard
from ui_theme import apply_theme, page_header
from ui_runtime import UI_LOCK, serialized_ui_operation
from detection import DetectionConfig
from pipeline import StreamingExperiment
from playback import PlaybackClock
from review import ReviewedRun
from run_catalog import completed_runs

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--review", type=Path)
args, _ = parser.parse_known_args()

st.set_page_config(page_title="CYBER DATA · Ciberseguridad y Big Data", page_icon="🛡️", layout="wide")
apply_theme()
if "clock" not in st.session_state:
    st.session_state.clock = PlaybackClock()
clock: PlaybackClock = st.session_state.clock
st.session_state.setdefault("review_path", str(args.review or Path(".")))


from home import render_home
st.session_state.setdefault("navigation", "Simulación" if args.review or "experiment" in st.session_state else "Inicio")
home_tab, simulation_tab = st.tabs(["Inicio", "Simulación"], key="navigation", on_change="rerun")
if home_tab.open:
    clock.pause()
    with home_tab:
        render_home()
    st.stop()

# Al volver de Inicio, el estado de las pestañas internas sigue disponible.
st.session_state.setdefault("dashboard_view", st.session_state.get("last_dashboard_view", "Fallos y Morris"))

with simulation_tab:
    page_header()


    @serialized_ui_operation
    def start() -> None:
        old = st.session_state.get("experiment")
        root = Path(st.session_state.get("runs_directory", "ejecuciones")) / uuid4().hex[:12]
        cfg = DetectionConfig(min_increase=float(st.session_state.get("threshold", 3)),
                              relative_increase=float(st.session_state.get("relative_threshold", 50))/100,
                              min_control_gap=float(st.session_state.get("control_threshold", 3)),
                              persistence=int(st.session_state.get("persistence", 3)))
        try:
            new = StreamingExperiment(root, detection_config=cfg)
        except (OSError, ValueError, RuntimeError) as exc:
            st.session_state.start_error = str(exc)
            clock.pause()
            return
        if old is not None:
            old.close()
        st.session_state.experiment = new
        st.session_state.pop("start_error", None)
        st.session_state.pop("processing_error", None)
        st.session_state.first_batch_requested = True
        clock.resume(monotonic(), immediate=True)
        st.session_state.confirm_reset = False


    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-mark">C</div><div><div class="brand-name">CYBER DATA</div><div class="brand-sub">Observatorio de autenticación</div></div></div>', unsafe_allow_html=True)
        st.subheader("Fuente de datos")
        mode = st.radio("Modo", ["Simulación", "Revisión"], index=1 if args.review else 0, key="mode", horizontal=True, persist_state="session", on_change="rerun")
        if st.session_state.get("previous_mode", mode) != mode:
            clock.pause()
        st.session_state.previous_mode = mode
        if mode == "Simulación":
            exp = st.session_state.get("experiment")
            frozen = exp is not None and not exp.is_finished
            st.caption("Genera y procesa desde el evento 1. Cada inicio conserva las ejecuciones anteriores.")
            st.divider()
            st.subheader("Reproducción")
            if exp is None:
                st.button("Iniciar simulación", on_click=start, key="start", type="primary", width="stretch")
            else:
                if st.button("Pausar" if clock.playing else "Reanudar", disabled=exp.is_finished or exp.failed, key="play", type="primary", width="stretch"):
                    clock.pause() if clock.playing else clock.resume(monotonic())
                if st.button("Siguiente lote", disabled=clock.playing or exp.is_finished or exp.failed, key="step", width="stretch"):
                    try:
                        with UI_LOCK:
                            exp.step()
                    except Exception as exc:
                        st.error(f"Error al procesar: {exc}")
            interval = st.select_slider("Segundos entre actualizaciones", options=[.1, .3, .6, 1.0, 2.0, 5.0], value=.6, key="speed", persist_state="session", on_change="rerun")
            if interval != clock.interval:
                clock.set_interval(interval, monotonic())
            st.caption("Primera proyección: 300. Después, un lote de 100 por actualización.")
            with st.expander("Configurar la próxima simulación"):
                st.text_input("Carpeta de ejecuciones", "ejecuciones", key="runs_directory", disabled=frozen)
                st.caption("Detector exploratorio: umbrales configurables antes del inicio.")
                st.number_input("Aumento mínimo (cuentas/min)", 0.1, 30.0, 3.0, .1, key="threshold", disabled=frozen)
                st.number_input("Aumento relativo mínimo (%)", 1.0, 500.0, 50.0, 5.0, key="relative_threshold", disabled=frozen)
                st.number_input("Diferencia mínima frente a Ámbar", .1, 30.0, 3.0, .1, key="control_threshold", disabled=frozen)
                st.number_input("Ventanas consecutivas", 1, 20, 3, key="persistence", disabled=frozen)
            if exp is not None:
                with st.expander("Reiniciar simulación"):
                    st.checkbox("Confirmo reiniciar esta simulación", key="confirm_reset", on_change="rerun")
                    st.button("Reiniciar", disabled=not st.session_state.confirm_reset, key="reset", on_click=start)
                    st.caption("Comienza otra ejecución y conserva los archivos recibidos.")
                st.caption(f"Ejecución local: {exp.output_dir}")
        else:
            clock.pause()
            st.caption("Explora una ejecución terminada con sus datos y resultados verificados.")
            available = completed_runs()
            if available:
                chosen = st.selectbox("Ejecuciones completas", available,
                                      format_func=lambda path: "Referencia incluida" if path == "." else path,
                                      key="review_choice", persist_state="session")
                if st.button("Abrir seleccionada", key="open_selected", width="stretch"):
                    st.session_state.review_path = chosen
                    st.session_state.review_requested = True
            st.text_input("Carpeta de la ejecución terminada", key="review_path", persist_state="session")
            load = st.button("Cargar ejecución", key="load_review", type="primary", width="stretch")
            requested = st.session_state.pop("review_requested", False)
            if load or requested or (args.review and "reviewed" not in st.session_state and "review_error" not in st.session_state):
                try:
                    with st.spinner("Verificando integridad, CSV y resultados…"):
                        st.session_state.reviewed = ReviewedRun(Path(st.session_state.review_path))
                    st.session_state.pop("review_error", None)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    st.session_state.pop("reviewed", None)
                    st.session_state.review_error = str(exc)
            st.caption("La revisión no genera eventos ni vuelve a entrenar los modelos.")
        st.divider()
        st.subheader("Protocolo del experimento")
        st.caption("6.000 resúmenes · 2 pasarelas\n\n300 eventos de ajuste · 5.700 de transformación\n\nMorris: 8 registros · K-means: 3 grupos")
        with st.expander("Semillas y reproducibilidad"):
            st.caption("Simulador, UMAP y K-means: 42. Morris: 420042, independiente del simulador. Ajuste inicial: ID 1–300, con 150 resúmenes por pasarela.")
        st.caption("Simulación académica. Los patrones y las alertas requieren contexto adicional para investigar un incidente real.")


    def install_playback_timer() -> None:
        # El fragmento solo procesa. Las pestañas viven en el árbol principal:
        # evita rutas delta inválidas al sustituir su contenido dinámicamente.
        first_render = True

        @st.fragment(run_every=clock.interval if clock.playing else None)
        @serialized_ui_operation
        def timer() -> None:
            nonlocal first_render
            requested = st.session_state.pop("first_batch_requested", False)
            if first_render:
                first_render = False
                if not requested:
                    return  # Montar/navegar/filtrar nunca consume el reloj.
            run = st.session_state.get("experiment")
            if run is None or run.failed or run.is_finished or not clock.playing:
                return
            if monotonic() < clock.next_due:
                return
            message = ("Procesando los primeros 300 eventos y ajustando UMAP y K-means; la primera ejecución puede compilar Numba…"
                       if run.event_count == 0 else "Transformando y clasificando el siguiente lote de 100 eventos…")
            try:
                with st.spinner(message):
                    processed = clock.tick(run, monotonic())
                if processed:
                    clock.next_due = monotonic() + clock.interval
                    st.rerun()
            except Exception as exc:
                clock.pause()
                st.session_state.processing_error = str(exc)
                st.rerun()

        timer()

    if mode == "Simulación":
        install_playback_timer()

    @serialized_ui_operation
    def live() -> None:
        if mode == "Revisión":
            if "review_error" in st.session_state:
                st.error(f"No se puede revisar: {st.session_state.review_error}. Selecciona una ejecución completa o corrige la ruta y pulsa Cargar ejecución.")
            run = st.session_state.get("reviewed")
            if run is None:
                st.info("Carga una ejecución terminada. La ejecución de referencia está en la carpeta «.».")
                return
            st.caption(f"Modo revisión · Integridad verificada · {run.output_dir}")
        else:
            if "start_error" in st.session_state:
                st.error(st.session_state.start_error)
            run = st.session_state.get("experiment")
            if run is None:
                st.info("Inicia una simulación desde la barra lateral o elige Revisión para explorar la ejecución guardada en «.».")
                st.subheader("Tres preguntas para interpretar el experimento")
                for column, title, text in zip(st.columns(3), ("¿Cuántos fallos?", "¿Qué patrones?", "¿Qué ha cambiado?"), ("Contrasta el recuento exacto de los CSV con los ocho registros Morris.", "Explora los puntos UMAP y caracteriza los tres grupos K-means.", "Compara cuentas, fallos e IP entre periodos y pasarelas."), strict=True):
                    with column, st.container(border=True):
                        st.markdown(f"**{title}**")
                        st.write(text)
                return
            if run.failed:
                clock.pause()
                st.error("Ejecución incompleta por un error de procesamiento. Los archivos recibidos se conservan; "
                         "utiliza el reinicio confirmado para comenzar otra ejecución.")
                st.progress(run.event_count/6000, text=f"{run.event_count} eventos recibidos antes del error")
                return
            if "processing_error" in st.session_state:
                st.error(f"La ejecución se ha detenido: {st.session_state.processing_error}")
            st.caption(f"Estado: {'finalizado' if run.is_finished else 'error' if run.failed else 'en marcha' if clock.playing else 'pausado'}")
        render_dashboard(run)


    live()
