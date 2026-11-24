"""Página de bienvenida: contexto del experimento, sin generar datos."""
import streamlit as st


def open_workspace() -> None:
    st.session_state.navigation = "Simulación"
    st.session_state.mode = "Simulación"


def open_reference() -> None:
    st.session_state.navigation = "Simulación"
    st.session_state.mode = "Revisión"
    st.session_state.review_path = "."
    st.session_state.review_requested = True


def render_home() -> None:
    st.markdown('''<style>
.home-hero{background:linear-gradient(120deg,#10243d,#183b61);border-radius:20px;padding:42px;color:white;margin-bottom:20px;position:relative;overflow:hidden}
.home-hero .tag{color:#9fc9ff;font-size:12px;letter-spacing:.15em;font-weight:700}
.home-hero h1{color:white;font-size:clamp(30px,3.4vw,48px);line-height:1.12;max-width:760px;margin:18px 0;padding:0}
.home-hero p{color:#d4e3f5;font-size:17px;line-height:1.7;max-width:770px}
.home-facts{display:flex;gap:32px;flex-wrap:wrap;border-top:1px solid #44617e;margin-top:28px;padding-top:22px}
.home-facts strong{display:block;color:white;font-size:25px}.home-facts span{font-size:13px;color:#bed1e6}
.home-card{height:100%;background:white;border:1px solid #dce5f0;border-radius:14px;padding:24px;margin:8px 0 16px}
.home-card .step{font-size:12px;letter-spacing:.1em;color:#2864dd;font-weight:700}.home-card h3{margin:12px 0!important}.home-card p{color:#52647b;line-height:1.65;font-size:15px}
.home-flow{display:flex;align-items:center;justify-content:space-between;gap:12px;background:#e8eff9;padding:24px;border-radius:14px;margin:16px 0 24px;color:#163c78;text-align:center;flex-wrap:wrap}
.home-flow b{display:block;font-size:16px}.home-flow small{font-size:13px;color:#52647b}
@media(max-width:760px){.home-hero{padding:26px}.home-facts{gap:20px}.home-flow{justify-content:center}.home-flow>div{min-width:120px}}
</style>
<section class="home-hero"><div class="tag">CYBER DATA / LABORATORIO DE CIBERSEGURIDAD</div>
<h1>Los fallos cuentan una parte.<br>Las cuentas revelan el cambio.</h1>
<p>Explora cómo cambia el comportamiento de dos pasarelas de autenticación. Sigue el flujo de accesos, descubre patrones y comprueba por qué un volumen similar de fallos puede afectar a muchas más cuentas.</p>
<div class="home-facts"><div><strong>6.000</strong><span>resúmenes del experimento</span></div><div><strong>2 pasarelas</strong><span>Ámbar y Cobalto</span></div><div><strong>3 técnicas</strong><span>Morris · UMAP · K-means</span></div></div></section>''', unsafe_allow_html=True)
    left, right = st.columns(2)
    left.button("Nueva simulación →" if "experiment" not in st.session_state else "Continuar simulación →", key="home_simulation", type="primary", width="stretch", on_click=open_workspace)
    left.caption("Configura y controla la reproducción. Los eventos empiezan al pulsar Iniciar.")
    right.button("Revisar resultados →", key="home_review", width="stretch", on_click=open_reference)
    right.caption("Abre la ejecución de referencia tras comprobar sus archivos e integridad.")
    st.subheader("¿Qué puedes descubrir?")
    cards = [("01 / MEDIR", "Cuánto está ocurriendo", "Compara el total exacto de intentos fallidos con la estimación de Morris. Observa cómo evoluciona el error de sus ocho registros por pasarela."),
             ("02 / EXPLORAR", "Qué patrones se repiten", "Recorre el mapa UMAP y sus tres grupos K-means. Filtra por pasarela y periodo para comprender las diferencias entre fallos concentrados y repartidos."),
             ("03 / COMPARAR", "Qué cambia en Cobalto", "Contrasta cuentas, fallos e IP antes y después. Utiliza Ámbar como referencia para interpretar el cambio con cifras calculadas en la ejecución.")]
    for column, (step, title, body) in zip(st.columns(3), cards, strict=True):
        with column:
            st.markdown(f'<article class="home-card"><div class="step">{step}</div><h3>{title}</h3><p>{body}</p></article>', unsafe_allow_html=True)
    st.subheader("Del evento a la explicación")
    st.markdown('''<div class="home-flow"><div><b>Dos pasarelas</b><small>Un resumen por minuto y origen</small></div><span>→</span><div><b>Datos y estimación</b><small>CSV separados + Morris</small></div><span>→</span><div><b>Patrones de acceso</b><small>UMAP + K-means</small></div><span>→</span><div><b>Evidencia verificable</b><small>Comparativas + informe PDF</small></div></div>''', unsafe_allow_html=True)
    a, b = st.columns(2)
    with a, st.container(border=True):
        st.subheader("Un experimento que puedes seguir")
        st.write("Inicia, pausa y avanza por lotes. La primera proyección aparece tras 300 eventos; el panel se actualiza cada 100 eventos posteriores. Al terminar, puedes descargar los CSV y el informe de defensa.")
    with b, st.container(border=True):
        st.subheader("Entender antes de concluir")
        st.write("Los datos son sintéticos. Los grupos describen patrones y las alertas señalan cambios de comportamiento; por sí solos no confirman un ataque real. Las cuentas se miden por minuto, no como usuarios únicos de toda la simulación.")
