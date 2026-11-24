# CYBER DATA — Auditoría 360º final

Fecha: 24/11/2026. Base: `7f76c40b7ba3c440f7b70cc182c3c098f1d85e11`. Fuente de requisitos: `enunciado_Trabajo_5.pdf`, leído completo antes de modificar código. No se asigna calificación oficial.

## Estado inicial y hallazgos confirmados

| Área | Hallazgo | Gravedad | Intervención |
|---|---|---|---|
| Performance | Se construían las tres vistas y los gráficos de desplegables cerrados; las descargas se releían | Media | Vista activa exclusiva, desplegables bajo demanda y caché de archivos finales |
| SEO/documentación | Título sin CYBER DATA; arranque disperso y distintos ficheros de requisitos en Windows | Media | Identidad común, README centrado en arranque, lock único |
| Design | Jerarquía ya funcional; texto ocre y rosa con contraste <4,5:1 sobre blanco | Media | Tonos más oscuros, sin cambiar semántica ni geometría de datos |
| Copy | «Estado normal» podía confundirse con evidencia de ausencia de incidentes | Media | Estado de detección condicionado al criterio y a lo observado |
| UX | Sin revisión directa desde Inicio; filtros perdían estado si no se renderizaban | Media | Dos accesos, catálogo de ejecuciones completas y persistencia de filtros |
| Evaluación | Instalación Windows duplicada, sin consentimiento winget; faltaban descargas analíticas directas | Media | Preparador compartido, confirmación, pip check y descargas JSON/proyecciones |
| Integridad de interacción | Un rerun de filtro podía consumir un vencimiento del reloj | Alta | Temporizador separado de la presentación; prueba con temporizador vencido |

Antes: 51 pruebas superadas en 52,87 s y `pip check` correcto. Una primera tentativa en la copia Definitivo falló por permisos de caché Numba fuera del sandbox; se repitió con acceso autorizado y pasó. No se atribuye esa restricción a un defecto del proyecto.

## Cambios implementados

Se conservan los modelos, semillas, lotes y algoritmos. Las pestañas nativas de Streamlit 1.67 construyen únicamente la vista activa; `persist_state="session"` mantiene los filtros. La selección de pestaña se guarda al navegar. El mapa conserva WebGL, los 6.000 puntos reales y `uirevision` por ejecución; añade ajuste inicial/transformados. Un arranque limpio confirmó que Streamlit 1.67 recrea el gráfico al cambiar su especificación y puede perder el zoom de arrastre. Se añadió un encuadre explícito de ejes guardado en la sesión, con validación de límites; la prueba comprueba su conservación contra los rangos reales de Plotly. No se afirma persistencia universal del zoom nativo. Los filtros nunca ajustan modelos ni escriben eventos.

Inicio ofrece Nueva simulación (o Continuar si ya existe) y Revisar resultados. La revisión directa valida la referencia antes de mostrarla. El catálogo muestra manifiestos completos con ML real y sin escritor activo; la validación íntegra se realiza al abrir la selección. El panel añade medias observadas de cuentas y fallos de ambas pasarelas, distingue esas medias de los KPI de la segunda mitad y muestra la comparación definitiva solo al finalizar.

Se conserva el bloqueo global de interfaz y `fastReruns=false`. QA detectó un error JavaScript «Bad delta path index» al cambiar reiteradamente pestañas dinámicas dentro de un fragmento. El fragmento ahora solo procesa el temporizador; después de un lote solicita el render de la página. Las pestañas viven en el árbol principal. El montaje inicial del temporizador no genera eventos, salvo al pulsar Iniciar/Reiniciar. La carga inicial informa del ajuste UMAP/K-means y de la posible compilación Numba. Los CSV siguen siendo la referencia exacta: leer ambos completos costó alrededor de 6 ms; no justificaba introducir una segunda fuente de verdad. Los filtros reutilizan el snapshot del último lote.

Las descargas no producen reruns y reutilizan bytes de los archivos finales. Se añaden resumen JSON y proyecciones CSV. Los registros Morris, el detector y el detalle numérico se construyen al desplegarlos. Se mantiene la guía de defensa y toda la funcionalidad anterior.

## Rendimiento: metodología y límites

Medición con `tools/performance_audit.py`, el mismo intérprete y dependencias para ambas versiones. Base extraída de Git en una carpeta temporal; ejecución anterior y posterior secuenciales, sin otras pruebas del agente en paralelo. Dos ejecuciones por proceso: primera y caliente. Se conserva la caché de disco Numba: **no es una instalación completamente fría**. El primer ajuste incluye importación diferida y compilación que proceda; el segundo reutiliza el proceso. La medición de ajuste engloba scaler, UMAP y K-means.

AppTest mide coste del servidor y construcción/serialización, no la latencia de pintura del navegador. Filtros: cinco alternancias de pasarela. Media/p95 de lotes sobre 57 lotes, incluyendo la exportación/PDF del último. Por ello la media puede superar el p95. RSS es el máximo acumulado del proceso, incluye ML y AppTest, y no aísla la memoria del dashboard. Una pareja por condición es evidencia local, no un benchmark estadístico general.

| Medida | Primera antes | Primera después | Caliente antes | Caliente después |
|---|---:|---:|---:|---:|
| Hasta 300 (s) | 8.096 | 7.833 | 0.567 | 0.566 |
| Ajuste inicial (s) | 8.023 | 7.760 | 0.499 | 0.497 |
| Lote media (s) | 0.138 | 0.134 | 0.097 | 0.095 |
| Lote p95 (s) | 0.110 | 0.088 | 0.095 | 0.091 |
| Ejecución completa (s) | 15.940 | 15.466 | 6.100 | 5.974 |
| Primera vista AppTest (s) | 1.338 | 0.816 | 0.603 | 0.230 |
| Filtro media (s) | 0.414 | 0.162 | 0.448 | 0.159 |
| Filtro p95 (s) | 0.430 | 0.171 | 0.566 | 0.170 |
| RSS máximo (MiB) | 363.5 | 434.1 | 370.6 | 434.1 |

En caliente, la media de filtros pasa de 448 a 159 ms y la primera vista de 603 a 230 ms. El motor permanece prácticamente igual (6,10 frente a 5,97 s); no se atribuye a la UI una aceleración de ML. El máximo RSS aumenta de 371 a 434 MiB: no hay mejora demostrada de memoria. Puede incluir cachés y asignaciones retenidas del proceso; no permite atribuir ese aumento a una función concreta.

Arranque medido con procesos nuevos y Chrome, sin otras pruebas del agente: salud del servidor 0,999 → 0,834 s; Inicio visible 5,084 → 4,480 s. Una muestra por versión, con caché de disco existente; no se generaliza a otras máquinas. Las importaciones del benchmark principal fueron 3,365 → 3,107 s.

El perfil de la vista inicial confirma que antes se construían Morris, mapa, matriz, distribuciones y comparación; después se construyen únicamente los dos gráficos Morris. Evidencias principales: `antes_controlado.json`, `despues_final.json`, `arranque.json`, `perfil_antes.json`, `perfil_despues.json`. Las mediciones intermedias se conservan identificadas, no se presentan como versión final.

## Resultados reales

| Pasarela | Exacto CSV | Morris | Diferencia | Error absoluto | Error relativo |
|---|---:|---:|---:|---:|---:|
| Ámbar | 97440 | 98303 | +863 | 863 | 0.885673 % |
| Cobalto | 98206 | 81919 | -16287 | 16287 | 16.584526 % |

Cobalto: cuentas de 4.149 a 18.100/min (+13.951; +336.28 %). Ámbar: -0.029 cuentas/min. Diferencia en diferencias: +13.981 cuentas/min. Los fallos cambian -0.243/min en Cobalto y +0.264/min en Ámbar (diferencia en diferencias: -0.507). El diseño conserva la esperanza de fallos (32,8/min) al cambiar el alcance; el recuento de fallos por sí solo no identifica ese mecanismo. Las cuentas son distintas por minuto; no representan personas únicas del periodo.

| Pasarela / mitad | Cuentas/min | Fallos/min | Grupo 0 | Grupo 1 | Grupo 2 |
|---|---:|---:|---:|---:|---:|
| Ámbar / Antes (1–3000) | 4.189 | 32.348 | 20.93 % | 69.13 % | 9.93 % |
| Ámbar / Después (3001–6000) | 4.159 | 32.612 | 20.20 % | 70.13 % | 9.67 % |
| Cobalto / Antes (1–3000) | 4.149 | 32.857 | 20.20 % | 70.07 % | 9.73 % |
| Cobalto / Después (3001–6000) | 18.100 | 32.614 | 20.07 % | 9.33 % | 70.60 % |

Los cuatro periodos contienen 1.500 resúmenes. Hay 6.000 coordenadas válidas, 300 de ajuste y 5.700 transformadas en 57 lotes; 58 puntos de actualización. Los tres centroides permanecen fijos.

Caracterización real de grupos (sin asignar significados por adelantado):

```json
[
  {
    "cluster": 0,
    "eventos": 1221,
    "accesos_medios": 54.97051597051597,
    "fallos_medios": 4.05077805077805,
    "cuentas_medias": 1.5053235053235052,
    "ips_medias": 1.5004095004095004,
    "interpretacion": "Predominio pocos fallos (100.0 %)"
  },
  {
    "cluster": 1,
    "eventos": 3280,
    "accesos_medios": 54.85609756097561,
    "fallos_medios": 39.92835365853659,
    "cuentas_medias": 1.9926829268292683,
    "ips_medias": 1.9960365853658537,
    "interpretacion": "Predominio fallos concentrados (100.0 %)"
  },
  {
    "cluster": 2,
    "eventos": 1499,
    "accesos_medios": 55.04869913275517,
    "fallos_medios": 39.84989993328886,
    "cuentas_medias": 25.030687124749832,
    "ips_medias": 11.996664442961974,
    "interpretacion": "Predominio fallos repartidos (100.0 %)"
  }
]
```

La correspondencia con perfiles alcanza 100 % en cada grupo en esta ejecución sintética; no demuestra rendimiento sobre tráfico real. Los CSV, proyecciones y estadísticas de la ejecución nueva son idénticos a la referencia, comprobados programáticamente (`validacion.json`). El PDF se generó con los resultados de esa ejecución.

## Accesibilidad y validación visual

El ocre de texto pasa de #B77A0B (3,62:1 sobre blanco) a #946008 (5,34:1), y el rosa de #C45074 (4,42:1) a #B93F65 (5,30:1). Las diez combinaciones de texto examinadas superan 4,5:1 (`contraste.json`), tomando como referencia [WCAG 2.2, contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Esto no acredita todos los estados ni una conformidad integral. Se añaden indicadores de foco; el mapa combina color con círculo/rombo/cuadrado y conserva los identificadores numéricos, etiquetas y tooltips. Morris distingue exacto/estimado con trazo continuo/punteado.

Capturas reales del inicio y las tres vistas en `capturas/`: [Inicio](capturas/inicio.png), [Morris](capturas/detalle_vista_1.png), [UMAP](capturas/detalle_vista_2.png), [Antes/después](capturas/detalle_vista_3.png), [móvil](capturas/movil_mapa.png). Se inspeccionaron visualmente inicio, mapa y móvil. No se utilizan imágenes de diseño ficticias como evidencia.

El recorrido completo de navegador ha terminado sin errores JavaScript ni excepciones Streamlit (`navegador.json`). Se comprueban la reproducción 1→6000, pausa, lote 400, velocidad, navegación, filtros, tooltip real, zoom, descargas, reinicio y 15 combinaciones de vista/anchura. Los fallos previos quedan documentados en el registro de progreso; no se contabilizan como pruebas superadas.

## Pruebas y comandos

```bash
.venv/bin/python -m pytest -q --junitxml=docs/auditoria_final/pytest.xml
.venv/bin/python -m pip check
bash ./PREPARAR_ENTORNO.sh
.venv/bin/python run_experiment.py --output-dir ejecuciones/auditoria_final
.venv/bin/python verificar.py --output-dir ejecuciones/auditoria_final --require-ml
.venv/bin/python tools/verify_browser.py --url http://127.0.0.1:8517 --simulate --screenshots docs/auditoria_final/capturas
.venv/bin/python tools/performance_audit.py despues_final
```

Resultado final: **55 pruebas superadas, 0 fallidas, 0 omitidas**, en 52,53 s (`pytest.xml`). Un aviso no bloqueante de joblib.

Las pruebas reales observan un `fit` del scaler, uno de UMAP y uno de K-means, 57 transformaciones y predicciones, centroides estables y cifras del PDF/JSON/CSV. No se usan mocks como única evidencia. El verificador de `auditoria_final` confirma integridad y modelos reales. El preparador macOS terminó correctamente y `pip check` no detectó incompatibilidades. El aviso de joblib sobre consulta de núcleos físicos dentro del sandbox no hizo fallar las pruebas; no se cambiaron semillas ni parámetros para evitarlo.

## AUDITORÍA DE CUMPLIMIENTO DE LA RÚBRICA — 10 PUNTOS

| Criterio académico | Puntos máximos | Evidencia | Prueba | Estado |
|---|---:|---|---|---|
| Generación y almacenamiento | 2 | 6.000 IDs, 3.000 filas por origen, tiempos pareados; `simulator.generate_events`, `CSVEventWriter` | `test_all_6000_ids_gateways_and_minute_pairs`, `test_exact_generation_probabilities_and_uniform_endpoints`, verificador real | VERIFICADO |
| Morris | 2 | Ocho registros, suma CSV 97.440/98.206, estimaciones 98.303/81.919; `Morris8.update`, `report.morris_metrics` | `test_morris_all_logical_increments_strict_probability_and_mean`, integración real | VERIFICADO |
| UMAP | 2 | 300 ajuste, 5.700 transformados, cuatro variables; `FixedUMAPClusters.fit_initial/transform_new` | `test_real_6000_single_training_no_future_refit`, `verificar.py --require-ml` | VERIFICADO |
| K-means | 2 | Tres centroides fijos, 6.000 asignaciones, frecuencias reales; `cluster_characterization`, `comparison_table` | Misma integración real y `test_group_percentages_and_heatmap_preserve_actual_counts` | VERIFICADO |
| Dashboard y defensa | 2 | Tres vistas, cuatro periodos de 1.500, CSV/JSON/PDF coherentes; `render_dashboard`, `calculate_defense` | AppTest, `test_real_statistics_csv_dashboard_pdf_agree`; Chrome completo (simulación, filtros, encuadre persistente, descargas, responsive y reinicio) | VERIFICADO |

## Archivos y limpieza

- `app.py`, `dashboard.py`, `home.py`, `ui_runtime.py`: navegación, temporizador, persistencia, vistas activas y revisión directa.
- `run_catalog.py`: catálogo de ejecuciones terminadas; `tests/test_run_catalog.py` verifica exclusión de parciales, bloqueadas, diagnósticas e inválidas.
- `bi_charts.py`, `ui_theme.py`: símbolos redundantes, colores, foco y encuadre persistente.
- `tests/test_dashboard.py`, `tests/test_home.py`: adaptación a vistas bajo demanda, conservación de filtros y bloqueo de generación al interactuar.
- `PREPARAR_WINDOWS.cmd`, `INICIAR_WINDOWS.cmd`, `PREPARAR_ENTORNO.sh`: lock común, consentimiento winget, verificaciones y mensajes de error.
- `tools/verify_browser.py`: recorrido real ampliado; `tools/performance_audit.py`, `tools/profile_ui.py`: medición reproducible.
- `README.md`: instalación primero, evaluación, arquitectura y límites; `docs/auditoria_final/`: informe, progreso, resultados y capturas. `docs/VALIDACION_GITHUB.md` anota la retirada posterior del CSS antiguo.
- Eliminados únicamente `assets/powerbi.css` y `assets/contraste_antes_despues.png`: búsquedas de referencias en código, pruebas, scripts y documentación no hallaron uso funcional; el CSS solo figuraba como conservación histórica. No pertenecían al manifiesto sellado.

Se conservan las capturas e informes anteriores como evidencia histórica de otras revisiones; no se confunden con las capturas finales. No se borran entornos ni datos personales del usuario. Los entregables sellados de referencia, dependencias y configuración ML permanecen intactos.

## Mejoras descartadas y limitaciones

No se añade SEO comercial, sitemap, analítica, autenticación, nuevas dependencias ni paralelismo. No se cambia el ajuste UMAP, los centroides, el número de registros o las distribuciones. La lectura incremental alternativa del CSV se descarta por su bajo coste y la complejidad de una segunda fuente exacta. El bloqueo de interfaz se conserva para garantizar snapshots completos y seguridad de Numba.

Windows nativo y Linux nativo no están disponibles para esta validación; no se afirma ejecución en esas plataformas. En Windows ejecutar `PREPARAR_WINDOWS.cmd`, `.\.venv\Scripts\python.exe -m pip check`, `.\.venv\Scripts\python.exe -m pytest -q` y `.\.venv\Scripts\python.exe -m streamlit run app.py`. No se hizo auditoría completa con lectores de pantalla ni conformidad WCAG. No se midió una instalación sin ninguna caché ni se aisló la memoria de cada componente. No hay puntuaciones Lighthouse ni nota oficial.

Descripción propuesta para GitHub: **CYBER DATA: laboratorio reproducible de ciberseguridad y Big Data en Streamlit, con Morris, UMAP y K-means sobre 6.000 eventos y defensa verificable.** Topics: `python`, `big-data`, `cybersecurity`, `streamlit`, `umap`, `k-means`, `morris`, `data-streaming`, `plotly`, `machine-learning`. Se proporcionan para configurar el apartado About; no se modifican sus metadatos como parte de esta auditoría.

Los enlaces externos del README a UMAP, Streamlit y scikit-learn respondieron correctamente; el repositorio se comprobó mediante el conector GitHub. Los enlaces locales se verifican al cerrar el informe (`enlaces.json`).

## Entrega local y Git

Cambios sincronizados con la carpeta Definitivo utilizada para arrancar Streamlit; se compararon los bytes de cada archivo copiado. La ejecución nueva también se conserva allí en `ejecuciones/auditoria_final`. Los archivos de referencia sellados permanecen intactos. Inventario: `archivos.json`. Los scripts CMD conservan terminadores CRLF; `git -c core.whitespace=cr-at-eol diff --check` no detecta errores de espacios.

Validación adicional en la carpeta de uso Definitivo: **55 pruebas superadas en 46,42 s**, `pip check` correcto y verificador de `ejecuciones/auditoria_final --require-ml` correcto. Evidencia: `pytest_definitivo.xml`.

Publicado en GitHub mediante push normal: commit `8a576cf`, «Optimiza CYBER DATA y valida la entrega académica de extremo a extremo». Sin cambios destructivos de Git ni alteración de los resultados de referencia.
