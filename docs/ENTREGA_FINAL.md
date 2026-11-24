# Entrega final — auditoría, implementación y validación

## A. Resumen de implementación

Se conservó el generador reproducible y el procedimiento matemático de Morris. Se añadieron guardas de contrato, validación estructural, ajuste único de los modelos, persistencia y metadatos, finalización compartida entre CLI/Streamlit, tres vistas ampliadas, controles de reproducción, revisión íntegra y detector causal. El PDF usa fuentes incluidas en ReportLab y tablas con ajuste de texto, contiene diagramas y se genera automáticamente con resultados reales.

Las correcciones incluyen: apertura de interfaz sin truncar datos, protección frente a dos escritores, archivado de ejecuciones, rechazo de proyecciones inválidas, errores que detienen el motor sin saltarse eventos, y distinción explícita entre una proyección de prueba y UMAP real. Los grupos mantienen su identificador y su interpretación depende del contraste observado; no se impone una asociación a priori.

## B. Matriz de cumplimiento

La tabla solicitada **«AUDITORÍA DE CUMPLIMIENTO DE LA RÚBRICA — 10 PUNTOS»** y la matriz detallada de cada apartado del PDF están en [CUMPLIMIENTO.md](CUMPLIMIENTO.md). Los cinco criterios tienen evidencia local y estado VERIFICADO. No se atribuye una nota oficial ni se garantiza un 10/10.

## C. Archivos modificados

| Archivo(s) | Acción y motivo |
|---|---|
| `config.py`, `simulator.py` | Conservación de distribuciones; configuración oficial validada; escritor rechaza ID repetidos y pasarelas incorrectas |
| `morris.py` | Conservación de f×8 incrementos; exige ocho registros y entradas enteras no negativas |
| `analytics.py` | Ajuste único con ID exactos, inferencia real, finitud, modelos, metadatos y carga local de confianza |
| `pipeline.py` | Motor incremental común, límites de lote oficiales, validación, gestión de fallo y finalización automática |
| `app.py` | Estado de sesión, controles, simulación/revisión y tratamiento de errores |
| `dashboard.py` (nuevo) | Tres vistas y gráficos, filtros, centroides, estadísticas compartidas y detección |
| `detection.py` (nuevo) | Ventanas causales, referencia observada y persistencia |
| `playback.py` (nuevo) | Reloj separado de datos; pausa/velocidad sin alterar resultados |
| `storage.py` (nuevo) | Rutas separadas, archivado, bloqueo, manifiesto SHA256 |
| `validation.py`, `review.py` (nuevos) | Validación de CSV/proyección y revisión sin generar ni entrenar |
| `report.py`, `pdf_report.py` | Estadísticas comunes, interpretación calculada, fuentes portables, PDF, diagramas, centroides y detector |
| `run_experiment.py`, `verificar.py` | CLI con finalización común y auditoría de datos/modelos |
| `requirements.txt` | Versiones exactas de las dependencias usadas |
| `requirements-lock.txt`, `requirements-browser.txt` (nuevos) | Entorno completo reproducible y QA de navegador opcional |
| `.streamlit/config.toml`, `pytest.ini` (nuevos) | Tema legible y configuración de pruebas |
| `.gitignore`, `README.md`, `INICIAR_WINDOWS.cmd`, `CHECKLIST_ENTREGA.md` | Instalación, arranque, límites, entregables y exclusiones justificadas |
| `tests/test_morris_pipeline.py`, `tests/test_verificacion_pdf.py` | Adaptación de rutas; un doble ya no acredita ML real; se preservan y refuerzan comprobaciones |
| `tests/conftest.py` (nuevo) | Ejecución real de 6000 eventos con observadores que llaman a los algoritmos originales |
| `tests/test_contracts.py`, `tests/test_real_full.py`, `tests/test_dashboard.py`, `tests/test_detection.py`, `tests/test_persistence_playback.py` (nuevos) | Contratos, integración, UI, detector, persistencia y errores |
| `tools/verify_browser.py` (nuevo) | Recorrido reproducible de Chrome con revisión, simulación, filtros, tooltip y capturas |
| `modelos/`, `resultados/`, `ejecucion.json` | Entregables reales de la ejecución completa |
| `docs/` | Auditoría inicial/final, resultados de pruebas, inventario y capturas |

No se eliminaron módulos necesarios. Los resultados antiguos mezclados en `datos/` se conservaron en `historial/` y se sustituyeron por los productos actuales organizados. El PDF antiguo de la raíz se archivó en `historial/documentos_originales/`. Los dos CSV actuales conservan exactamente los mismos datos reproducibles. `PREPARAR_WINDOWS.cmd` apareció como archivo vacío durante la sesión y se dejó intacto; no forma parte de los cambios implementados.

## D. Resultados numéricos

| Pasarela | Exacto | Morris | Diferencia | Error absoluto | Error relativo |
|---|---:|---:|---:|---:|---:|
| Ámbar | 97440 | 98303 | +863 | 863 | 0.8857 % |
| Cobalto | 98206 | 81919 | -16287 | 16287 | 16.5845 % |

Cobalto: cuentas de 4.149 a 18.100/min (+13.951; +336.28 %). Ámbar: -0.029 cuentas/min. Diferencia en diferencias: +13.981 cuentas/min. Los fallos cambian -0.243/min en Cobalto y +0.264/min en Ámbar (diferencia en diferencias: -0.507). El diseño conserva la esperanza de fallos (32,8/min) al cambiar el alcance; el recuento de fallos por sí solo no identifica ese mecanismo. Las cuentas son distintas por minuto; no representan personas únicas del periodo.

## E. Resultados de Machine Learning

300 puntos de entrenamiento y 5700 puntos nuevos transformados; **6000 coordenadas y etiquetas válidas**. Tres centroides fijos; un único ajuste real de scaler, UMAP y K-means. Los perfiles fueron excluidos del aprendizaje.

| Grupo real | Eventos | Fallos/min | Cuentas/min | IP/min | Contraste observado |
|---|---:|---:|---:|---:|---|
| 0 | 1221 | 4.051 | 1.505 | 1.500 | Predominio pocos fallos (100.0 %) |
| 1 | 3280 | 39.928 | 1.993 | 1.996 | Predominio fallos concentrados (100.0 %) |
| 2 | 1499 | 39.850 | 25.031 | 11.997 | Predominio fallos repartidos (100.0 %) |

| Pasarela / mitad | Grupo 0 | Grupo 1 | Grupo 2 |
|---|---:|---:|---:|
| Ámbar / Antes (1–3000) | 20.93 % | 69.13 % | 9.93 % |
| Ámbar / Después (3001–6000) | 20.20 % | 70.13 % | 9.67 % |
| Cobalto / Antes (1–3000) | 20.20 % | 70.07 % | 9.73 % |
| Cobalto / Después (3001–6000) | 20.07 % | 9.33 % | 70.60 % |

Cada fila corresponde a 1500 resúmenes. La correspondencia grupo/perfil es del 100 % en esta simulación, calculada después del entrenamiento. No es una medida de detección de incidentes reales ni garantiza el resultado para otros datos o versiones.

## F. Pruebas

**39 pruebas superadas; cero fallidas, errores u omitidas (56.19 s).**

La relación de comandos, resultados, evidencia de las llamadas reales y límites está en [VALIDACION.md](VALIDACION.md), con [JUnit XML](pytest-resultados.xml) y [registro Chrome](navegador.json).

```bash
.venv/bin/python -m pytest -q --junitxml=docs/pytest-resultados.xml
.venv/bin/python run_experiment.py
.venv/bin/python verificar.py --require-ml
.venv/bin/python pdf_report.py
.venv/bin/python -m pip check
.venv/bin/python tools/verify_browser.py --simulate
```

Además de verificar las funciones, se completó una ejecución desde Chrome y se compararon sus dos CSV, toda la proyección y el resumen JSON con la ejecución de CLI: coincidieron. El PDF se verificó mediante extracción de texto y renderizado de sus cinco páginas.

## G. Limitaciones

La prueba nativa en Windows sigue pendiente: el entorno disponible es macOS. La aplicación conserva una simulación durante los reruns de una sesión, pero no ofrece recuperación de una sesión parcial tras cerrar el proceso. Las ejecuciones terminadas sí se recuperan desde disco. No se validaron cargas de producción ni tráfico real. La reproducibilidad entre otras versiones/plataformas no se garantiza. Los hashes detectan alteraciones; no hacen confiable un modelo externo. Morris y el detector tienen las limitaciones probabilísticas y exploratorias descritas en el informe.

## H. Ejecución en VSCode

Desde la raíz, en PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
# Ver los resultados terminados:
.\.venv\Scripts\python.exe -m streamlit run app.py -- --review .
```

En macOS: `.venv/bin/python -m streamlit run app.py`. Con entorno activado: `python -m streamlit run app.py`. No se necesita una cuenta externa ni publicar la aplicación.

## I. Git

La carpeta carecía de `.git`; por tanto no se puede ofrecer un `git diff` o un estado de cambios pendientes del remoto desde este checkout. [cambios_archivos.json](cambios_archivos.json) registra las diferencias observadas frente a la copia inicial. No se inicializó Git, no se hizo commit, push ni despliegue. Se conservaron los archivos ajenos detectados durante la sesión.

Mensaje de commit sugerido: `feat: validar el experimento Big Data y completar dashboard, modelos e informe reproducibles`.
