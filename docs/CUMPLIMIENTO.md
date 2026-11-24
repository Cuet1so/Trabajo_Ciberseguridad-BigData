# AUDITORÍA DE CUMPLIMIENTO DE LA RÚBRICA — 10 PUNTOS

Actualización: 24/11/2026. Fuente oficial: `enunciado_Trabajo_5.pdf`, idéntico al PDF aportado. Esta tabla acredita requisitos comprobados; **no asigna una nota oficial ni garantiza un 10/10**. La prueba de navegador se suma a las pruebas automatizadas de Streamlit; la ejecución nativa en Windows queda pendiente.

| Criterio de evaluación | Puntuación máxima | Requisitos comprobados | Archivo o función responsable | Prueba ejecutada | Evidencia obtenida | Estado |
|---|---:|---|---|---|---|---|
| Generación y almacenamiento por origen | 2 | 6.000 eventos, ID 1–6000, orden Ámbar/Cobalto, parejas temporales, 08:00, rangos inclusivos, probabilidades correctas, CSV incremental y 3.000 filas por origen | `simulator.generate_events`, `CSVEventWriter.write`; `validation.validate_raw` | `test_all_6000_ids_gateways_and_minute_pairs`; `test_exact_generation_probabilities_and_uniform_endpoints`; `test_writer_incremental_order_reset_and_closed`; integración real | `datos/ambar.csv`, `datos/cobalto.csv`; `verificar.py`: 6000 eventos / 3000 minutos / integridad correcta | VERIFICADO |
| Algoritmo Morris y contraste exacto | 2 | Ocho registros en cero, f×8 sorteos por evento, umbral estricto, RNG separado, media de 2^c−1, exacto desde CSV y errores | `Morris8.update`, `Morris8.estimate`, `GatewayMorris`; `report.morris_metrics` | `test_morris_all_logical_increments_strict_probability_and_mean`; `test_simulator_rng_unaffected_by_morris`; integración y revisión | Ámbar 97.440 exactos / 98.303 estimados; Cobalto 98.206 / 81.919; registros y errores en JSON/PDF/vista 1 | VERIFICADO |
| Proyección de nuevos eventos con UMAP | 2 | Cuatro variables; scaler y UMAP ajustados una sola vez sobre 300 eventos globales; 150 por pasarela; 57 transformaciones de 100; 6.000 puntos finitos; sin reajuste | `FixedUMAPClusters.fit_initial`, `transform_new`; `StreamingExperiment.step` | `test_real_6000_single_training_no_future_refit`; `test_umap_real_fit_first_300_and_transform_next_100`; reutilización del modelo persistido | Observadores de llamadas reales: scaler.fit=1, UMAP.fit=1, transform=57; `eventos_proyectados.csv`; modelos y metadatos | VERIFICADO |
| Agrupamiento K-means e interpretación | 2 | Tres centroides sobre proyección inicial; 57 predict sin reajuste; centros estables; medias por grupo; contraste con perfiles y porcentajes por periodo | `FixedUMAPClusters`; `cluster_characterization`; `comparison_table` | `test_real_6000_single_training_no_future_refit`; `test_real_statistics_csv_dashboard_pdf_agree`; `verificar.py --require-ml` | Grupos con 1221/3280/1499 puntos; matrices y frecuencias calculadas, centroides comprobados contra predict | VERIFICADO |
| Dashboard y defensa con resultados numéricos | 2 | Tres vistas; primer mapa 300, actualización cada 100; filtros y tooltip; 1500 observaciones por mitad; defensa cuantificada y reproducible | `app.live`, `dashboard.render_dashboard`, `report.calculate_defense`, `pdf_report.build_defense_pdf` | `test_real_dashboard_three_views_and_gateway_filter`; `test_first_display_at_300_and_no_duplicate_rerun`; pruebas de filtros/controles/revisión; Chrome con `--simulate` | Tres vistas renderizadas; flujo real 1→6000; PDF de 5 páginas; cambio Cobalto +13,951 cuentas/min (+336,28 %), fallos −0,243/min; diferencia en diferencias +13,981 cuentas/min | VERIFICADO |

La [auditoría 360º final](auditoria_final/INFORME.md) añade la validación actual de 55 pruebas, Chrome, rendimiento y accesibilidad parcial. Los modelos y requisitos oficiales se conservan.

## Matriz detallada del PDF

En esta tabla, **Implementado y verificado** significa ejecución y evidencia observada en el entorno local, sin afirmar validación en otros sistemas operativos.

| Referencia | Requisito | Archivo / función | Estado final | Verificación |
|---|---|---|---|---|
| §1.1 | 6000 eventos consecutivos, sin saltos | `generate_events` | Implementado y verificado | `test_all_6000_ids_gateways_and_minute_pairs` |
| §1.1 | Dos/minuto, Ámbar impar primero, Cobalto par, mismo instante | `generate_events`, `validate_raw` | Implementado y verificado | Misma prueba y validador temporal |
| §1.1 | Inicio 08:00 y semilla fija | `ExperimentConfig` | Implementado y verificado | Inicio 2026-11-10T08:00, semilla 42, reproducibilidad |
| §1.1 | Tres perfiles y cuatro sorteos uniformes inclusivos | `PROFILE_RANGES`, `generate_events` | Implementado y verificado | Pruebas de rangos y extremos de llamada a `integers(lo, hi+1)` |
| §1.1 | 20/70/10 antes; 20/10/70 solo en Cobalto después | `DISTRIBUTIONS`, `generate_events` | Implementado y verificado | Observación de las 6000 llamadas con sus probabilidades; sin forzar frecuencias |
| §1.2 | Almacenar cada evento por origen desde el primero | `CSVEventWriter.write` | Implementado y verificado | Lectura tras primer evento y flush; conteos reales al terminar |
| §1.2 | Cabecera, perfil y 3000 filas por CSV | `CSV_COLUMNS`, `validate_raw` | Implementado y verificado | `verificar.py`, pruebas de valores corruptos |
| §1.2 | Archivos nuevos vacíos | `RunLease`, `CSVEventWriter` | Implementado y verificado | Reinicio archiva, escritor nuevo solo tiene cabeceras |
| §2.1 | Ocho registros independientes por pasarela, inicialmente cero | `Morris8`, `GatewayMorris` | Implementado y verificado | Inicialización, rechazo de 16 registros, RNG distintos |
| §2.1 | Procesar f intentos por cada registro; u < 2^−c | `Morris8.update` | Implementado y verificado | Conteo f×8 de llamadas y prueba de igualdad al umbral |
| §2.1 | Media de ocho 2^c−1 y exacto desde CSV | `estimate`, `morris_metrics`, `calculate_defense` | Implementado y verificado | Media conocida, errores, suma CSV y replay Morris |
| §2.2 | Solo cuatro medidas, excluidos ID/tiempo/pasarela/perfil | `SecurityEvent.features` | Implementado y verificado | Matriz real (300,4) idéntica a cuatro columnas CSV |
| §2.2 | Ajustar scaler y UMAP 2D con los primeros 300 globales | `fit_initial` | Implementado y verificado | Un fit real; entrada de UMAP igual al escalado inicial |
| §2.2 | Conservar ajustes y transformar los siguientes | `transform_new` | Implementado y verificado | 57 lotes; 5700 puntos transformados; parámetros y embedding intactos |
| §2.3 | Tres centroides sobre proyección inicial y semillas | `fit_initial` | Implementado y verificado | K-means.fit=1 sobre (300,2), n_clusters=3 |
| §2.3 | Asignar nuevos eventos al centro más cercano | `transform_new` | Implementado y verificado | predict=57; verificación geométrica y modelo persistido |
| §2.3 | Medias por grupo y contraste posterior de perfiles | `cluster_characterization` | Implementado y verificado | 6000 etiquetas; matriz de correspondencia; sin significado fijo del ID |
| §2 | Contar desde el primero, visualizar 300 y luego cada 100 | `StreamingExperiment.step`, `render_dashboard` | Implementado y verificado | Historial completo [300,400,…,6000], pruebas de pasos individuales y UI |
| §3.1 | Vista de exacto/Morris/diferencia con unidades | `render_dashboard` | Implementado y verificado | AppTest, Chrome, CSV y PDF con las mismas cifras |
| §3.2 | Mapa coloreado, filtro pasarela y tooltip minuto/fallos/cuentas/IP | `render_dashboard`, `filter_points` | Implementado y verificado | AppTest, filtros Chrome y campos Plotly |
| §3.3 | Medias y % grupo en 1500 resúmenes por pasarela/mitad | `comparison_table`, `metric_changes` | Implementado y verificado | Cuatro periodos de 1500; porcentajes suman 100 |
| §3.3 | Contraste repartidos con perfiles y significado por minuto | `cluster_characterization`, `interpretation` | Implementado y verificado | Tabla grupos/perfiles, texto explícito y cifras en PDF |
| Entrega | Generador, dashboard, dependencias y arranque | Scripts, requirements, README | Implementado y verificado | CLI, importación, `pip check`, Streamlit y Chrome locales |
| Defensa | Error Morris; cambio Cobalto; comparación con Ámbar y solo fallos | `calculate_defense`, PDF | Implementado y verificado | Prueba de cifras extraídas del PDF, cinco páginas renderizadas |

## Ampliaciones del usuario

| Ampliación | Evidencia | Estado |
|---|---|---|
| Evolución de error y ocho estimaciones individuales | Vista 1 y capturas; 16 filas de registros | VERIFICADO |
| Filtros de periodo/grupo, centroides y matriz de calor | Pruebas AppTest con cada combinación, selección vacía y Chrome | VERIFICADO |
| Variaciones, perfiles, diferencia en diferencias | Tablas compartidas con JSON/PDF; prueba de sumas porcentuales | VERIFICADO |
| Detector sin datos futuros | `test_causal_reference_persistence_detects_shift_at_unannounced_time`, prueba de prefijos, normalidad y pico breve; detección real ID 3160 | VERIFICADO |
| Pausa, reanudación, reinicio confirmado y velocidad | AppTest, PlaybackClock y simulación completa de navegador | VERIFICADO |
| Modelos y metadatos persistidos | Guardado/recarga real, transformación reproducida; rechazo de archivos corruptos y sin confianza | VERIFICADO |
| Revisión sin generación ni ajuste | Generador/ajuste prohibidos durante test; mismas métricas en UI | VERIFICADO |
| Windows/PowerShell | Rutas relativas, fuentes portables y comandos documentados | PARCIAL: no se dispone de ejecución nativa Windows |
| Recuperar sesión parcial tras cerrar proceso | Limitación explícita; se conserva ejecución parcial y se rechaza como terminada | No ofrecido; pausa/reanudación se garantiza durante la sesión activa |
