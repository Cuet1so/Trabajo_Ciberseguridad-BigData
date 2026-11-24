# Auditoría 360º — registro de continuidad

Estado actual: P0–P3 completados. Checkout Definitivo sincronizado, validado y publicado.
Base Git: `7f76c40b7ba3c440f7b70cc182c3c098f1d85e11` (main). Sin cambios ajenos en el checkout Definitivo al inspeccionarlo.
Desarrollo: copia Ciberseguridad_Big_Data_Tiempo_Real; destino de uso: Definitivo/Trabajo5-Ciberseguridad_BigData_Tiempo_Real.
Servidor de QA propio: puerto 8517. No detener el servidor del usuario en 8502.

- P0: PDF íntegro leído; 51 pruebas iniciales pasan, pip check correcto.
- P1: vistas activas, snapshot reutilizado, caché de descargas, revisión directa y catálogo, instalación con lock común y validación.
- P2: contraste corregido, símbolos por grupo, foco, textos precisos, encuadre persistente, separación temporizador/presentación para corregir error JS confirmado.
- P3: README simplificado; informe y matriz redactados; limpieza de dos recursos sin uso. Ejecución nueva en ejecuciones/auditoria_final validada con --require-ml e idéntica a referencia en CSV, proyecciones y cifras; referencia sin cambios.
- Benchmark definitivo: antes_controlado.json vs despues_final.json. Filtro caliente 448→159 ms; motor 6,10→5,97 s; RSS 371→434 MiB. No afirmar mejora de memoria ni aceleración de ML.
- Pruebas: último pase previo al encuadre 54/54; pase con encuadre y navegador completados. Registro final: pytest.xml y navegador.json (comprobar fechas/resultados antes de entregar).
- QA: hubo un recorrido completo válido sin errores JS, pero arranque limpio reveló límite de uirevision. Mecanismo explícito de encuadre implementado y prueba real del rango añadida. No afirmar que el zoom nativo siempre persiste.
- Windows/Linux nativos y auditoría WCAG integral pendientes por entorno.

Comandos principales ejecutados: `bash ./PREPARAR_ENTORNO.sh`; `.venv/bin/python run_experiment.py --output-dir ejecuciones/auditoria_final`; `.venv/bin/python verificar.py --output-dir ejecuciones/auditoria_final --require-ml`; `.venv/bin/python -m pytest -q --junitxml=docs/auditoria_final/pytest.xml`; `.venv/bin/python tools/verify_browser.py --url http://127.0.0.1:8517 --simulate --screenshots docs/auditoria_final/capturas`; `.venv/bin/python tools/performance_audit.py despues_final`.

Publicación: el usuario autorizó expresamente subir los cambios a GitHub en un mensaje anterior. Usar commit normal y push sin fuerza, solo después de validar y sincronizar los archivos auditados. Reconfirmar HEAD y ausencia de cambios ajenos antes de copiar. No sobrescribir otros directorios o ejecuciones.

## Historial de incidencias y decisiones

Incidencia QA confirmada: Streamlit emitía «Bad delta path index» tras alternar pestañas dinámicas dentro del fragmento. Corregido separando temporizador (fragmento) y presentación (árbol principal). El primer montaje del temporizador no procesa, salvo petición explícita de Iniciar/Reiniciar. Se retiran callbacks skip_tick ya innecesarios. Tres vistas x cinco anchos pasan sin error JS; se corrige selector de etiqueta del checkbox de reinicio (input nativo oculto). Repetir recorrido final y medición tras este ajuste.

QA tras arranque limpio: se confirmó que la versión instalada de Streamlit recrea Plotly al cambiar especificación; uirevision no garantiza conservar el zoom de arrastre. Se añadió encuadre explícito con cuatro límites persistentes y validación de orden/finitud. Se mantiene prueba de zoom nativo como observación de capacidad y se verifica el mecanismo alternativo contra rangos Plotly, sin ocultar la limitación. Repetir benchmark, pytest y Chrome final.

Cierre de validación: 55/55 pruebas en 52,53 s; Chrome completo supera los controles, encuadre persistente y 15 combinaciones responsive, sin errores JavaScript. El zoom nativo no persiste al recrear Plotly, limitación registrada explícitamente.

Sincronización completada con comparación byte a byte, conservando Git y archivos sellados. Copiada también la ejecución nueva auditoria_final; 54 archivos auditados más manifiesto de cambios. `git diff --check` con cr-at-eol correcto (scripts CMD usan CRLF).

Destino validado: 55 pruebas en 46,42 s, pip check y verificador ML real correctos. Preparado commit normal de la auditoría; no se modificaron los entregables sellados de referencia.

Publicación completada: commit `8a576cf` en `origin/main`, push normal confirmado. Árbol de trabajo limpio tras publicar. Validación local final: 55 pruebas, pip check y verificador ML real correctos; Chrome sin errores JS. No quedan tareas funcionales pendientes; limitaciones de Windows/Linux nativos, accesibilidad integral y zoom nativo documentadas.
