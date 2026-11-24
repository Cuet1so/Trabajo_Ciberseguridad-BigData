# Integración con GitHub — 24/11/2026

Destino autorizado: [Cuet1so/Trabajo_Ciberseguridad-BigData](https://github.com/Cuet1so/Trabajo_Ciberseguridad-BigData), rama `main`.

Se preparó el rediseño local sobre el commit remoto `2eebb4bebd37f988ecf0bb57b5a75879fd196284` conservando su historial y todos los archivos remotos existentes.

## Diferencias integradas

- Se conserva `PREPARAR_WINDOWS.cmd`, el CSS anterior `assets/powerbi.css` y las pruebas `tests/test_bi_metrics.py`, que solo estaban en GitHub. La interfaz actual utiliza `ui_theme.py`; el CSS anterior no se carga.
- Se mantienen las funciones públicas `evolution_by_gateway` y `gateway_kpis` del `bi_metrics.py` remoto junto a las funciones del rediseño.
- Se conserva la mejora remota de `storage.versions`: registra las dependencias ausentes durante un diagnóstico, en lugar de abortar la consulta de versiones.
- Se conserva la aclaración remota de `run_experiment.py`: una ejecución con `--sin-ml` no habilita el modo revisión ni satisface la rúbrica completa.
- Se incorporan el rediseño, las pruebas nuevas, las capturas, la documentación y los archivos necesarios para reproducir el trabajo.
- El lanzador local `INICIAR_WINDOWS.cmd` y `PREPARAR_ENTORNO.sh` conservan la instalación reproducible con `requirements-lock.txt`.

Las modificaciones de integración no cambian la generación, Morris, UMAP, K-means ni los datos de referencia. La comprobación SHA-256 de `redisenoui_integridad.json` corresponde al cierre del rediseño anterior a esta integración; posteriormente se incorporó exclusivamente la mejora remota descrita de `storage.py` entre los módulos allí enumerados.

## Validación de la versión integrada

```bash
.venv/bin/python -m pytest -q --junitxml=docs/pytest-github.xml
.venv/bin/python verificar.py --require-ml
```

- **49 pruebas superadas**, 0 fallidas, 0 omitidas; 57,85 segundos. Incluye los dos casos adicionales del repositorio remoto y la integración con UMAP/scikit-learn reales.
- **Integridad correcta:** 6.000 eventos, 3.000 minutos, 3.000 filas por pasarela; proyección real disponible.
- Fallos exactos: Ámbar **97.440**, Cobalto **98.206**. Morris: **98.303** y **81.919**, respectivamente.
- El aviso de joblib sobre núcleos físicos en el entorno restringido no afecta al resultado.

Evidencias: [JUnit de integración](pytest-github.xml), [validación visual del rediseño](REDISENO_UI.md), [navegador](navegador_ui.json) y [capturas](capturas_ui/).

Se respetan las exclusiones de `.gitignore`: entornos virtuales, cachés, credenciales, temporales, históricos y ejecuciones redundantes. Se incluyen los CSV, modelos, informe PDF y metadatos de referencia como entregables del trabajo. Windows sigue pendiente de ejecución nativa; no se modifica esa limitación documentada.

Nota de auditoría 24/11/2026: se retiró `assets/powerbi.css` tras comprobar que no tenía referencias funcionales; los estilos vigentes están en `ui_theme.py`.
