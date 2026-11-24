# Validación ejecutada — 17/11/2026

Entorno: macOS, Python 3.12.2. Todas las cifras siguientes proceden de `resultados/resumen_defensa.json`, comprobado contra los CSV y la proyección de la ejecución actual.

## Comandos y resultados

| Comando (raíz del proyecto) | Resultado observado |
|---|---|
| `.venv/bin/python -m pytest -q` antes de editar | 9 superadas, 1 fallida: tamaño del PDF dependiente de la fuente del sistema |
| Pruebas originales tras corregir | 10 superadas |
| Suite del núcleo de la rúbrica | 25 superadas; integración real y tres vistas |
| `.venv/bin/python -m pytest -q --junitxml=docs/pytest-resultados.xml` | 39 superadas, 0 fallidas, 0 errores, 0 omitidas; 56.19 s |
| `.venv/bin/python run_experiment.py` | 6000 eventos reales; generación, CSV, Morris, UMAP, K-means, estadísticas, modelos y PDF |
| `.venv/bin/python verificar.py --require-ml` | Integridad correcta; 6000 eventos, 3000 minutos; modelos persistidos comprobados |
| `.venv/bin/python pdf_report.py` | PDF de 5 páginas regenerado y manifiesto actualizado |
| `.venv/bin/python -m pip check` | `No broken requirements found.` |
| `.venv/bin/python -m compileall -q ...` | Todos los módulos, pruebas y herramienta de navegador compilan |
| Streamlit en 127.0.0.1:8501 | Servidor iniciado; HTTP 200 y WebSocket aceptado |
| `.venv/bin/python tools/verify_browser.py --simulate` | Chrome real: tres vistas, revisión, filtros, primera proyección 300, pausa, rerun, lote 400, reanudación y final 6000; sin errores JavaScript |

Existe un aviso de joblib en el entorno restringido: no puede consultar núcleos físicos y usa núcleos lógicos. No causa fallos; UMAP conserva `n_jobs=1`. La instalación y el navegador requirieron permisos de red/proceso, concedidos durante la sesión.

## Evidencia de los cinco criterios

- CSV: exactamente 3000 filas por origen; ID, tipos, perfiles, rangos y cronología validados. Las probabilidades se comprueban inspeccionando las llamadas del generador, sin exigir frecuencias empíricas exactas.
- Morris: número de sorteos f×8, comparación estricta con el umbral, fuentes aleatorias separadas, promedio y errores contrastados contra CSV.
- ML: observadores que llaman a las implementaciones reales de scaler/UMAP/K-means. Un `fit` por modelo, matriz inicial (300,4), UMAP inicial (300,2), 57 `transform` de (100,4) y 57 `predict` de (100,2). Se comparan scaler, embedding y centroides antes/después.
- Estadísticas: cuatro periodos de 1500 filas; los porcentajes de grupos y de perfiles suman 100 %; 6000 coordenadas finitas y etiquetas 0–2.
- Dashboard/defensa: mismos cálculos para CLI, revisión, simulación y PDF. Los CSV, la tabla proyectada y el resumen JSON de la simulación real en navegador resultaron idénticos a los de la CLI.
- PDF: texto extraído con pypdf para comprobar totales, estimaciones, errores, registros, 13.951, 336.3 %, 32.857, 32.614 y 13.981; cinco páginas renderizadas para inspección de tablas y diagramas.

## Resultados de Morris

| Pasarela | Exacto CSV | Morris | Diferencia | Error absoluto | Error relativo | Registros |
|---|---:|---:|---:|---:|---:|---|
| Ámbar | 97440 | 98303 | +863 | 863 | 0.885673 % | [16, 15, 17, 17, 17, 17, 17, 15] |
| Cobalto | 98206 | 81919 | -16287 | 16287 | 16.584526 % | [16, 15, 17, 17, 16, 16, 15, 17] |

## Comparación temporal

| Pasarela / periodo | N | Fallos/min | Cuentas/min | IP/min | Grupo 0 | Grupo 1 | Grupo 2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ámbar / Antes (1–3000) | 1500 | 32.348000 | 4.188667 | 2.838667 | 20.9333 % | 69.1333 % | 9.9333 % |
| Ámbar / Después (3001–6000) | 1500 | 32.612000 | 4.159333 | 2.882000 | 20.2000 % | 70.1333 % | 9.6667 % |
| Cobalto / Antes (1–3000) | 1500 | 32.856667 | 4.148667 | 2.878667 | 20.2000 % | 70.0667 % | 9.7333 % |
| Cobalto / Después (3001–6000) | 1500 | 32.614000 | 18.100000 | 8.975333 | 20.0667 % | 9.3333 % | 70.6000 % |

Cobalto: cuentas de 4.149 a 18.100/min (+13.951; +336.28 %). Ámbar: -0.029 cuentas/min. Diferencia en diferencias: +13.981 cuentas/min. Los fallos cambian -0.243/min en Cobalto y +0.264/min en Ámbar (diferencia en diferencias: -0.507). El diseño conserva la esperanza de fallos (32,8/min) al cambiar el alcance; el recuento de fallos por sí solo no identifica ese mecanismo. Las cuentas son distintas por minuto; no representan personas únicas del periodo.

## Grupos realmente obtenidos

| Grupo | N | Fallos/min | Cuentas/min | IP/min | Contraste posterior |
|---|---:|---:|---:|---:|---|
| 0 | 1221 | 4.050778 | 1.505324 | 1.500410 | Predominio pocos fallos (100.0 %) |
| 1 | 3280 | 39.928354 | 1.992683 | 1.996037 | Predominio fallos concentrados (100.0 %) |
| 2 | 1499 | 39.849900 | 25.030687 | 11.996664 | Predominio fallos repartidos (100.0 %) |

La correspondencia de cada grupo con su perfil predominante es 100 % **en esta ejecución sintética**. Se calculó mediante tabla cruzada; no se impuso al entrenamiento y no se interpreta como rendimiento de detección de ataques reales.

## Detector y persistencia

Primera detección: ID **3160**, instante simulado **2026-11-11T10:19**. Cobalto: 15.710 cuentas/min, referencia 3.906667, aumento 11.803333; aumento diferencial frente a Ámbar 12.360. Persistencia: 3 ventanas evaluadas. No se utilizó el perfil ni el ID 3001 como criterio de activación.

Modelos cargados desde archivos locales de confianza, versiones y SHA256 comprobados. Se reprodujo la proyección real del lote 301–400 con los modelos cargados. El modo revisión se probó con las funciones de generación y ajuste bloqueadas para detectar cualquier llamada indebida. La corrupción de un archivo impide la revisión antes de deserializar modelos.

## Límites explícitos

- No se ejecutó Windows/PowerShell nativamente. Se prepararon rutas portables, fuentes incluidas en ReportLab, instrucciones e instalador para Python 3.12.
- No se prueba rendimiento de alta carga ni datos de tráfico real: el alcance es el experimento local de 6000 resúmenes.
- La pausa mantiene la sesión del proceso. La recuperación de una simulación parcial tras cerrar el proceso no está implementada; se conserva como incompleta y se inicia otra ejecución.
- La reproducibilidad se comprobó en el entorno fijado. No se garantiza identidad numérica entre plataformas/versiones distintas.
- No hay `.git` en la carpeta: no se pudieron producir estado o diff Git locales. Se preparó inventario de archivos; no se hicieron commit, push ni publicaciones.

## Evidencias conservadas

- [Rúbrica y matriz detallada](CUMPLIMIENTO.md).
- [Resultados de pytest en JUnit XML](pytest-resultados.xml).
- [Registro de simulación en navegador](navegador.json), [verificación del tooltip y revisión](navegador_revision.json) y [capturas](capturas/).
- [Informe PDF](../resultados/Informe_Defensa_Tecnica.pdf) y [datos de defensa](../resultados/resumen_defensa.json).
- [Metadatos ML](../modelos/metadatos.json) y [manifiesto SHA256](../ejecucion.json).
