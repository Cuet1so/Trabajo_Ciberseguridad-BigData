# Security Intelligence — Ciberseguridad en tiempo real

Dashboard local **estilo Power BI** desarrollado con **Streamlit + Plotly**. Cumple el proyecto de *Computación Masiva para Big Data*: genera 6.000 resúmenes sintéticos de autenticación, registra CSV separados para Ámbar y Cobalto, estima fallos mediante Morris (8 registros/pasarela), representa la actividad con UMAP bidimensional y agrupa los eventos en tres clústeres mediante K-means.

El panel conserva **tres vistas exigidas en el trabajo**: (1) exacto vs Morris; (2) mapa de actividad UMAP con filtros y contraste de perfiles; (3) antes y después, con 1.500 minutos por pasarela y mitad. Los modelos se ajustan una sola vez sobre los primeros 300 eventos; los 5.700 siguientes se proyectan sin reentrenar. Las actualizaciones se producen en los eventos 300, 400, 500, …, 6000.

## Requisitos

- Python **3.12**; VSCode recomendado.
- Conexión a Internet para instalar paquetes la primera vez.
- Dependencias declaradas en **`requirements.txt`** (`streamlit`, `plotly`, `umap-learn`, `scikit-learn`, `numpy`, `pandas`, `reportlab`, `pytest`, etc.).
- No se necesita Microsoft Power BI, servidor externo, licencia ni API.

## Windows — dos comandos en VSCode

Abre la carpeta del proyecto (donde está `app.py`) y selecciona **Terminal → Nuevo terminal** (PowerShell).

**1. Preparación automática (una sola vez):**

```powershell
.\PREPARAR_WINDOWS.cmd
```

El script detecta Python 3.12; si falta intenta instalarlo con `winget`. Después crea `.venv`, instala `requirements.txt` y comprueba Streamlit, UMAP y scikit-learn. Si winget no está disponible, instala Python 3.12 manualmente e inténtalo de nuevo.

**2. Arrancar la aplicación:**

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abre <http://localhost:8501>. Pulsa `Ctrl+C` en la terminal para detenerla.

**Alternativa:** ` .\INICIAR_WINDOWS.cmd ` prepara y ejecuta automáticamente el dashboard.

## macOS / Linux — zsh o bash

```bash
bash ./PREPARAR_ENTORNO.sh
.venv/bin/python -m streamlit run app.py
```

El script de macOS/Linux requiere Python 3.12 instalado previamente. Si el entorno ya está activado (`(.venv)`), basta con `python -m streamlit run app.py`. Los `.cmd` son únicamente para Windows.

## Defensa: revisar resultados incluidos sin esperar a simular

En Windows:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py -- --review .
```

En macOS/Linux:

```bash
.venv/bin/python -m streamlit run app.py -- --review .
```

En modo **Revisión** se verifican los hashes y se recalculan estadísticas desde los CSV y proyecciones. No se regeneran eventos ni se vuelven a entrenar modelos. En modo **Simulación** puedes iniciar, pausar, reanudar y avanzar por lotes, con velocidad ajustable y reinicio confirmado. Cada simulación nueva crea una carpeta en `ejecuciones/` para conservar las anteriores.

## Pruebas y reproducibilidad

```bash
python -m pytest -q                  # con .venv activo
python verificar.py --require-ml     # valida la ejecución de referencia y los modelos locales de confianza
python run_experiment.py            # nueva ejecución completa; archiva los resultados previos
```

Para crear una ejecución de defensa independiente y no sobrescribir los resultados de referencia: `python run_experiment.py --output-dir ejecuciones/defensa`.

**Cuidado con `joblib`:** carga únicamente los modelos generados en tu propio equipo y en un entorno de confianza. El modo Revisión no los deserializa.

## Archivos de la entrega

| Archivo o carpeta | Función |
|---|---|
| `app.py`, `dashboard.py`, `assets/powerbi.css` | Interfaz Power BI-like con tres vistas |
| `simulator.py`, `morris.py`, `analytics.py`, `pipeline.py` | Generación, contadores, ML y procesamiento incremental |
| `detection.py`, `bi_metrics.py`, `report.py`, `pdf_report.py` | Detección opcional, estadísticas e informe de defensa |
| `datos/` | `ambar.csv` y `cobalto.csv` (3.000 filas cada uno) |
| `resultados/` | Puntos UMAP, historiales, métricas y `Informe_Defensa_Tecnica.pdf` |
| `modelos/` | Modelos ajustados y metadatos (solo archivos locales de confianza) |
| `ejecucion.json` | Manifiesto SHA256 de los resultados guardados |
| `tests/`, `verificar.py` | Pruebas y comprobación de integridad |
| `requirements.txt` | Dependencias instalables |
| `PREPARAR_WINDOWS.cmd`, `INICIAR_WINDOWS.cmd`, `PREPARAR_ENTORNO.sh` | Preparación y arranque |

Los resultados provienen de una **simulación sintética**. Los clústeres muestran patrones, no una prueba de ataque real. Las cuentas distintas por minuto no equivalen al número de cuentas únicas en todo el periodo.
