# Auditoría inicial — 17/11/2026

Fuente: `Trabajo_5.pdf`, dos páginas; la copia `enunciado_Trabajo_5.pdf` es idéntica byte a byte. Las instrucciones del PDF se utilizan como requisitos del producto solicitado.

Entorno: Python 3.12.2, entorno `.venv` existente. Esta carpeta carece de `.git`; no se modificó el remoto. Se conservó una copia previa fuera del proyecto durante la intervención.

Prueba inicial: `.venv/bin/python -m pytest -q`: **9 passed, 1 failed** (21,79 s). Falló `test_validation_and_pdf_generation`: PDF de 9571 bytes frente al mínimo de 10000. El informe dependía de fuentes Linux y recurría a Helvetica en macOS. UMAP real sí estaba instalado y su prueba inicial pasó.

## Matriz inicial de requisitos oficiales

| PDF | Requisito | Implementación inicial | Estado inicial | Evidencia / hueco |
|---|---|---|---|---|
| 1.1 | 6000 ID, pares temporales, Ámbar primero, inicio 08:00 | config, simulator | Implementado y verificado | test_simulator |
| 1.1 | Perfiles, enteros inclusivos, cambio solo Cobalto | config, simulator | Implementado y verificado | Rangos verificados; faltaba probar probabilidades exactas del generador |
| 1.2 | Dos CSV, 3000 filas, escritura desde ID 1 | simulator, pipeline | Implementado, pero necesita corrección | Reinicio automático destructivo al abrir dashboard; sin protección concurrente |
| 2.1 | Morris: ocho registros, f incrementos, RNG separado | morris | Implementado y verificado | Pruebas de reproducibilidad; faltaba inspección de sorteos y umbral estricto |
| 2.1 | Exacto desde CSV y diferencia | report, app | Implementado y verificado | Cifras reproducidas por las pruebas |
| 2.2 | Cuatro variables, ajuste con ID 1–300, transform posterior | analytics, pipeline | Implementado, pero necesita corrección | Admite reajustar y entrenar con 300 ID incorrectos; sin persistencia ni finitud |
| 2.3 | Tres centroides iniciales, asignación fija | analytics | Parcialmente implementado | No impide reajuste; clasificación de patrones presupone tres perfiles distintos |
| 2.3 | Caracterización y contraste con perfiles | report, app | Parcialmente implementado | Medias y cruce existentes; falta justificar interpretación y visualizar cruce |
| 2 | Dibujar 300; actualizar 400…6000 | pipeline, app | Parcialmente implementado | Lotes nominales correctos, reruns de widgets pueden avanzar el motor |
| 3.1 | Vista Morris y unidades | app | Implementado y verificado | Faltan pruebas UI y evolución del error solicitadas por el usuario |
| 3.2 | Mapa, filtro pasarela, tooltip | app | Pendiente de validación por limitaciones del entorno | No había pruebas de dashboard; ahora se instalará/comprobará lo disponible |
| 3.3 | 1500 resúmenes por mitad, medias y frecuencias | report, app | Parcialmente implementado | Muestra periodos incompletos; falta verificación de porcentajes |
| 3 | Defensa cuantificada y arranque | pdf_report, README | Implementado, pero necesita corrección | PDF falla; documentación dice ML no ejecutado aunque está instalado |

## Dependencias y flujo encontrados

`config → simulator → pipeline → analytics / morris`; `report → pipeline`; `pdf_report` consume el resumen; CLI y Streamlit duplican la finalización. `session_state` conserva el motor pero abrir una sesión nueva trunca los CSV. Los productos analíticos están mezclados con datos y no hay metadatos ni modelos persistidos.

## Ampliaciones solicitadas

No implementadas inicialmente: revisión íntegra, modelos joblib y manifiesto, detector causal, velocidad configurable, reinicio confirmado, periodos/grupos como filtros, centroides, matriz de calor, gráficos de variaciones, pruebas completas de interfaz/integridad. La matriz final y las pruebas ejecutadas se documentan en `CUMPLIMIENTO.md` y `VALIDACION.md`.
