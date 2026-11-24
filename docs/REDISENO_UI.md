# Rediseño y validación del dashboard — 24/11/2026

El cambio se concentra en la presentación de Streamlit y Plotly. Se conservan las tres vistas, el experimento de 6.000 eventos y las funciones compartidas con el informe. No se modifican los algoritmos ni sus parámetros.

## Problemas observados y solución

| Problema de la interfaz anterior | Cambio implementado |
|---|---|
| La conclusión principal quedaba después de tablas y gráficos extensos | Resumen superior con cuentas y fallos de Cobalto, comparación frente a Ámbar y eventos analizados |
| Los colores de pasarelas y grupos podían confundirse | Ocre/azul para pasarelas; verde/púrpura/rosa para los ID reales de los grupos |
| Demasiados elementos con el mismo peso visual | Tarjetas, paneles blancos, navegación de tres pestañas y detalles en desplegables |
| Ejes y cifras con formatos poco consistentes | Unidades explícitas, formato español, tooltips y barras desde cero |
| El mapa exigía interpretar una tabla extensa | Tres tarjetas calculadas para los grupos seleccionados, centroides C0–C2 y correspondencia con perfiles |
| Los filtros cambiaban la escala del mapa | Límites estables calculados con la ejecución observada, sin recalcular UMAP |
| Reruns de filtros repetían lecturas y agregados | Una copia de presentación por ejecución/lote; se invalida al avanzar o cargar otra ejecución |

La comparación final se habilita únicamente con cuatro periodos de 1.500 resúmenes. El perfil real sigue utilizándose solo para auditoría posterior. Las tablas completas, ocho registros Morris, evolución del error, detector, descargas y controles permanecen accesibles.

## Recorrido para la defensa

1. **Resumen:** Cobalto pasa de 4,149 a 18,100 cuentas/min: +13,951 (+336,28 %). Sus fallos pasan de 32,857 a 32,614/min: −0,243 (−0,74 %).
2. **Fallos y Morris:** contrasta los totales CSV de Ámbar (97.440) y Cobalto (98.206) con las estimaciones 98.303 y 81.919. Los errores relativos son 0,89 % y 16,58 %; son resultados probabilísticos reales.
3. **Mapa:** muestra los 300 eventos iniciales y los 5.700 transformados; explora cada grupo y su contraste con los perfiles. Los centroides permanecen fijos.
4. **Antes y después:** compara cuentas y fallos con Ámbar como referencia. La diferencia en diferencias de cuentas es +13,981/min. Las barras y porcentajes se calculan con los datos observados.
5. **Guía de defensa y descargas:** relaciona las cinco evidencias con los criterios de dos puntos del profesor. La interfaz no asigna una nota.

## Corrección de concurrencia detectada durante QA

El recorrido en Chrome expuso un solapamiento entre una actualización automática y un control manual. Una lectura pudo observar filas aún sin proyección y Numba abortó por acceso concurrente a su capa `workqueue`.

`ui_runtime.py` serializa las operaciones de interfaz con un bloqueo compartido entre sesiones del servidor. `app.py` lo aplica al inicio, avance manual y fragmento de procesamiento/visualización. La configuración `runner.fastReruns=false` permite terminar el trabajo nativo en curso antes del rerun. No se cambia el motor ni el número de eventos de cada lote. La pausa puede esperar a que termine el lote activo.

La prueba `test_ui_serializes_processing_and_reads` fuerza una proyección pendiente y comprueba que la lectura espera y recibe 300 filas completamente proyectadas. El recorrido posterior en navegador completó 6.000 eventos y produjo CSV, proyección e historiales idénticos a los de referencia.

Referencias técnicas: [configuración de reruns de Streamlit](https://docs.streamlit.io/develop/api-reference/configuration/config.toml), [hilos en Streamlit](https://docs.streamlit.io/develop/concepts/design/multithreading) y [capas de ejecución de Numba](https://numba.readthedocs.io/en/stable/user/threading-layer.html).

## Pruebas ejecutadas

Entorno: macOS, Python 3.12.2 y las dependencias fijadas del proyecto.

| Validación | Resultado |
|---|---|
| Suite antes de modificar | 39 pruebas superadas |
| Pruebas de presentación y Streamlit | 13 superadas; KPI/CSV, filtros, restablecimiento, caché, gráficos y controles |
| Suite completa: `python -m pytest -q --junitxml=docs/pytest-ui.xml` | 47 superadas, 0 fallidas, 0 omitidas; 72,54 s |
| Integración real de la suite | 6.000 eventos; un ajuste por modelo, 300 iniciales, 57 transformaciones de 100 y centroides invariables |
| `python verificar.py --require-ml` | Integridad correcta, 6.000 eventos, modelos reales y totales CSV coincidentes |
| Reproducción real en Chrome | Inicio, primera vista 300, pausa, filtro sin avance, lote 400, cambio de velocidad, reanudación y fin 6000 |
| Filtros y descargas en Chrome | Tres grupos conservados al cambiar de modo y finalizar; restablecimiento, tooltips y descarga de ambos CSV y PDF correctos |
| Revisión móvil a 390 píxeles | Sin desbordamiento horizontal; mapa con 6.000 puntos y centroides visibles; sin errores JavaScript |
| Igualdad de la reproducción con la referencia | CSV de ambas pasarelas, proyección, JSON de defensa y ambos historiales idénticos byte a byte |
| Conservación del núcleo | SHA-256 sin cambios en 12 módulos del experimento |

El aviso de joblib sobre la consulta de núcleos físicos en el entorno restringido no causa fallos; utiliza los núcleos lógicos. Las pruebas de aprendizaje ejecutan realmente UMAP y scikit-learn. Las pruebas rápidas con dobles de prueba son complementarias.

El recorrido final se ejecutó con `python tools/verify_browser.py --url http://127.0.0.1:8517 --simulate` sobre una vista previa local. La ejecución completa resultante es `ejecuciones/eb7898f3d45a`; sus 58 puntos de actualización son 300, 400, …, 6000. Los metadatos registran 300 eventos de entrenamiento y 5.700 transformados en 57 lotes. La selección inicial de grupos se comprobó tanto en el evento 300 como al finalizar y en móvil, después de corregir su pérdida al remontar el selector durante un cambio de modo.

## Archivos

| Archivo | Responsabilidad |
|---|---|
| `app.py` | Barra lateral, bienvenida y coordinación de la sesión |
| `dashboard.py` | Tres vistas, resumen, filtros, detalles y guía de defensa |
| `bi_metrics.py` — nuevo | Datos de presentación y formato; reutiliza las estadísticas de `report.py` |
| `bi_charts.py` — nuevo | Figuras Plotly verificables sin modificar datos |
| `ui_theme.py` — nuevo | Paletas, CSS, tarjetas, contraste y configuración de gráficos |
| `ui_runtime.py` — nuevo | Exclusión de operaciones de interfaz concurrentes |
| `.streamlit/config.toml` | Tema principal/lateral y comportamiento de reruns |
| `tests/test_dashboard.py` | Controles, formato español, caché, filtros y restablecimiento |
| `tests/test_bi_presentation.py` — nuevo | Correspondencia de KPI, barras, mapa, Morris y porcentajes con datos reales |
| `tests/test_ui_runtime.py` — nuevo | Lecturas coherentes durante operaciones simultáneas |
| `tools/verify_browser.py` | QA reproducible, descargas y capturas de escritorio/móvil |
| `README.md` | Navegación, arquitectura de presentación y ejecución de QA |

No se eliminan archivos del proyecto. Las simulaciones de QA se guardan en carpetas nuevas de `ejecuciones/`; la ejecución de referencia no se sobrescribe. Se conserva también el ensayo incompleto que permitió detectar la carrera.

## Evidencias y ejecución

- [JUnit: suite completa](pytest-ui.xml).
- [Recorrido completo del navegador](navegador_ui.json).
- [Conservación del núcleo y resultados](redisenoui_integridad.json).
- [Resumen y comparación antes/después](capturas_ui/vista_3.png).
- [Morris y error](capturas_ui/detalle_vista_1.png).
- [Mapa, grupos y perfiles](capturas_ui/detalle_vista_2.png).
- [Captura móvil](capturas_ui/movil.png) y [mapa móvil](capturas_ui/movil_mapa.png).

Desde la raíz en macOS:

```bash
.venv/bin/python -m streamlit run app.py -- --review .
```

En otra terminal, con Chrome instalado:

```bash
.venv/bin/python tools/verify_browser.py --simulate
```

Para generar desde cero, omite `-- --review .` y pulsa **Iniciar simulación**. Los comandos equivalentes de Windows están en el README.

La validación de navegador se realiza en Chrome local y con anchuras de 1.440 y 390 píxeles. No se ha ejecutado Windows nativo, Safari ni una prueba de carga multiusuario. Los estilos están comprobados con la versión fijada de Streamlit; una actualización futura debe repetir esta revisión visual. La carpeta de trabajo carece de `.git`: no se han realizado commit, push ni publicaciones.
