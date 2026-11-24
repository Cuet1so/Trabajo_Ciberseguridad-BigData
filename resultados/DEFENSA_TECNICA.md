# Defensa técnica y conclusiones — Ciberseguridad en tiempo real

**Trabajo final · Computación Masiva para Big Data**

## 1. Arquitectura y trazabilidad

El simulador crea 6.000 eventos (3.000 por pasarela), dos por minuto con un mismo instante: 
Ámbar recibe los IDs impares y Cobalto los pares. Los CSV se escriben incrementalmente 
desde el primer evento. La semilla de simulación es 42; el contador Morris utiliza una 
fuente aleatoria diferente (semilla 420042, ramificada por pasarela).

Las cuatro entradas de UMAP son accesos correctos, fallos, cuentas e IP de origen. 
El escalador y la proyección se ajustan exclusivamente con los primeros 300 eventos 
globales. K-means (k=3) se entrena sobre esa proyección; después solo se aplican 
StandardScaler.transform, UMAP.transform y KMeans.predict.

## 2. Cuantificación del error de Morris

Cada fila representa un resumen por minuto, pero Morris procesa tantos incrementos 
como intentos fallidos contenga la fila, para cada uno de los ocho registros.

| Pasarela | Fallos exactos CSV | Morris (media de 8) | Diferencia firmada | Error absoluto | Error relativo |
|---|---:|---:|---:|---:|---:|
| Ámbar | 97,440 | 98,303.00 | +863.00 | 863.00 | 0.89 % |
| Cobalto | 98,206 | 81,919.00 | -16,287.00 | 16,287.00 | 16.58 % |

Fórmulas: **error absoluto = |Morris − exacto|**; **error relativo = 100 × error absoluto / exacto**.

Registros finales (c₁,...,c₈): Ámbar = [16, 15, 17, 17, 17, 17, 17, 15]; Cobalto = [16, 15, 17, 17, 16, 16, 15, 17].

## 3. Resultados antes y después

Cada periodo contiene **1.500 resúmenes por pasarela**, equivalentes a 1.500 minutos.

| Pasarela / periodo | Fallos medios/min | Cuentas medias/min | IP medias/min | Perfil repartido (%) |
|---|---:|---:|---:|---:|
| Ámbar — antes | 32.348 | 4.189 | 2.839 | 9.93 |
| Ámbar — después | 32.612 | 4.159 | 2.882 | 9.67 |
| Cobalto — antes | 32.857 | 4.149 | 2.879 | 9.73 |
| Cobalto — después | 32.614 | 18.100 | 8.975 | 70.60 |

### Cambios observados (segunda mitad − primera mitad)

- **Cobalto:** cuentas **+13.951 cuentas/min**, fallos **-0.243 fallos/min**, IP **+6.097 IP/min**.
- **Ámbar (control):** cuentas **-0.029 cuentas/min**, fallos **+0.264 fallos/min**, IP **+0.043 IP/min**.
- **Diferencia en diferencias (Cobalto − Ámbar):** +13.981 cuentas/min; -0.507 fallos/min.

## 4. ¿Habría bastado observar únicamente los fallos?

**No de forma fiable.** Los dos perfiles con muchos fallos comparten el intervalo 30–50. Al cambiar su mezcla de 70 % concentrados / 10 % repartidos a 10 % concentrados / 70 % repartidos, la cantidad **esperada** de fallos permanece constante. No obstante, crecen las cuentas e IP de origen afectadas. Cualquier variación pequeña de la media de fallos observada en la muestra responde a fluctuaciones aleatorias, no al mecanismo del cambio programado. Ámbar permanece con la distribución original y actúa como pasarela de control.

No se deben sumar cuentas distintas por minuto para obtener cuentas únicas en todo el periodo: una misma cuenta podría aparecer en varios resúmenes. Tampoco se afirma que un grupo K-means confirme por sí solo un ataque real; faltaría investigar logs originales.

## 5. UMAP y caracterización de K-means

Los números de grupo (0, 1 y 2) son etiquetas arbitrarias. Se interpretan por las medias de accesos correctos, fallos, cuentas e IP, y se contrastan con los perfiles reales de simulación.

| Grupo | Eventos | Fallos/min | Cuentas/min | IP/min | Interpretación |
|---|---:|---:|---:|---:|---|
| 0 | 1221 | 4.05 | 1.51 | 1.50 | Predominio pocos fallos (100.0 %) |
| 1 | 3280 | 39.93 | 1.99 | 2.00 | Predominio fallos concentrados (100.0 %) |
| 2 | 1499 | 39.85 | 25.03 | 12.00 | Predominio fallos repartidos (100.0 %) |

**Porcentaje de pertenencia a cada grupo por mitad:**

| Pasarela / mitad | Grupo 0 (%) | Grupo 1 (%) | Grupo 2 (%) |
|---|---:|---:|---:|
| Ámbar — antes | 20.93 | 69.13 | 9.93 |
| Ámbar — después | 20.20 | 70.13 | 9.67 |
| Cobalto — antes | 20.20 | 70.07 | 9.73 |
| Cobalto — después | 20.07 | 9.33 | 70.60 |

La composición de cada grupo por perfil real está guardada también en `resumen_defensa.json`, sección `pureza_por_cluster_porcentaje`. Esa comparación sirve para validar la interpretación, no para entrenar los grupos.

## 6. Reproducibilidad y limitaciones

- La fecha inicial simulada es el 10/11/2026 a las 08:00; el periodo comprende 3.000 minutos.
- Los intervalos de enteros incluyen ambos extremos.
- La semilla 42 fija perfiles y medidas; las otras semillas fijan los algoritmos aleatorios.
- Se preserva el mismo escalador, UMAP y K-means después del evento 300.
- La semilla no hace iguales los resultados entre versiones diferentes de las dependencias: se aconseja conservar un entorno virtual estable.
- La estimación Morris es aleatoria; aunque con ocho registros mejora respecto a una única copia, no debe presentarse como recuento exacto.

**Referencia de requisitos:** `Trabajo_5.pdf` aportado en el enunciado.

## 7. Interpretación calculada

Cobalto: cuentas de 4.149 a 18.100/min (+13.951; +336.28 %). Ámbar: -0.029 cuentas/min. Diferencia en diferencias: +13.981 cuentas/min. Los fallos cambian -0.243/min en Cobalto y +0.264/min en Ámbar (diferencia en diferencias: -0.507). El diseño conserva la esperanza de fallos (32,8/min) al cambiar el alcance; el recuento de fallos por sí solo no identifica ese mecanismo. Las cuentas son distintas por minuto; no representan personas únicas del periodo.

## 8. Detección exploratoria causal

```json
{
  "configuracion": {
    "window": 100,
    "baseline_events": 300,
    "stride": 20,
    "persistence": 3,
    "min_increase": 3.0,
    "relative_increase": 0.5,
    "min_control_gap": 3.0
  },
  "referencia": {
    "Ámbar": 4.096666666666667,
    "Cobalto": 3.9066666666666667
  },
  "primera_deteccion": {
    "id": 3160,
    "instante": "2026-11-11T10:19",
    "minuto": 1580,
    "cuentas_Ámbar": 3.54,
    "cuentas_Cobalto": 15.71,
    "fallos_Ámbar": 33.17,
    "fallos_Cobalto": 33.15,
    "evaluable": true,
    "candidato": true,
    "persistencia": 3,
    "cambio_observado": true,
    "aumento_cobalto": 11.803333333333335,
    "diferencia_control": 12.360000000000001,
    "umbral": 3.0,
    "referencia_cobalto": 3.9066666666666667,
    "referencia_ambar": 4.096666666666667
  }
}
```

Referencia fijada con observaciones iniciales; sin usar perfiles ni el ID del cambio. Las ventanas se solapan y su persistencia no equivale a pruebas estadísticas independientes.

## 9. Modelos y reproducibilidad

```json
{
  "variables": [
    "accesos_correctos",
    "fallos",
    "cuentas",
    "ips_origen"
  ],
  "ids_entrenamiento": [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    36,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    52,
    53,
    54,
    55,
    56,
    57,
    58,
    59,
    60,
    61,
    62,
    63,
    64,
    65,
    66,
    67,
    68,
    69,
    70,
    71,
    72,
    73,
    74,
    75,
    76,
    77,
    78,
    79,
    80,
    81,
    82,
    83,
    84,
    85,
    86,
    87,
    88,
    89,
    90,
    91,
    92,
    93,
    94,
    95,
    96,
    97,
    98,
    99,
    100,
    101,
    102,
    103,
    104,
    105,
    106,
    107,
    108,
    109,
    110,
    111,
    112,
    113,
    114,
    115,
    116,
    117,
    118,
    119,
    120,
    121,
    122,
    123,
    124,
    125,
    126,
    127,
    128,
    129,
    130,
    131,
    132,
    133,
    134,
    135,
    136,
    137,
    138,
    139,
    140,
    141,
    142,
    143,
    144,
    145,
    146,
    147,
    148,
    149,
    150,
    151,
    152,
    153,
    154,
    155,
    156,
    157,
    158,
    159,
    160,
    161,
    162,
    163,
    164,
    165,
    166,
    167,
    168,
    169,
    170,
    171,
    172,
    173,
    174,
    175,
    176,
    177,
    178,
    179,
    180,
    181,
    182,
    183,
    184,
    185,
    186,
    187,
    188,
    189,
    190,
    191,
    192,
    193,
    194,
    195,
    196,
    197,
    198,
    199,
    200,
    201,
    202,
    203,
    204,
    205,
    206,
    207,
    208,
    209,
    210,
    211,
    212,
    213,
    214,
    215,
    216,
    217,
    218,
    219,
    220,
    221,
    222,
    223,
    224,
    225,
    226,
    227,
    228,
    229,
    230,
    231,
    232,
    233,
    234,
    235,
    236,
    237,
    238,
    239,
    240,
    241,
    242,
    243,
    244,
    245,
    246,
    247,
    248,
    249,
    250,
    251,
    252,
    253,
    254,
    255,
    256,
    257,
    258,
    259,
    260,
    261,
    262,
    263,
    264,
    265,
    266,
    267,
    268,
    269,
    270,
    271,
    272,
    273,
    274,
    275,
    276,
    277,
    278,
    279,
    280,
    281,
    282,
    283,
    284,
    285,
    286,
    287,
    288,
    289,
    290,
    291,
    292,
    293,
    294,
    295,
    296,
    297,
    298,
    299,
    300
  ],
  "eventos_entrenamiento": 300,
  "eventos_transformados": 5700,
  "lotes_transformados": [
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100
  ],
  "eventos_procesados": 6000,
  "semillas": {
    "simulador": 42,
    "morris": 420042,
    "umap": 42,
    "transform": 42,
    "kmeans": 42
  },
  "versiones": {
    "python": "3.12.2",
    "numpy": "2.5.5",
    "pandas": "2.3.3",
    "scipy": "1.18.1",
    "scikit-learn": "1.9.1",
    "umap-learn": "0.5.12",
    "numba": "0.68.1",
    "llvmlite": "0.50.0",
    "pynndescent": "0.7.0",
    "joblib": "1.6.0",
    "streamlit": "1.67.0",
    "plotly": "6.9.0",
    "reportlab": "4.5.1"
  },
  "parametros": {
    "scaler": {
      "copy": true,
      "with_mean": true,
      "with_std": true
    },
    "umap": {
      "a": null,
      "angular_rp_forest": false,
      "b": null,
      "dens_frac": 0.3,
      "dens_lambda": 2.0,
      "dens_var_shift": 0.1,
      "densmap": false,
      "disconnection_distance": null,
      "force_approximation_algorithm": false,
      "init": "spectral",
      "learning_rate": 1.0,
      "local_connectivity": 1.0,
      "low_memory": true,
      "metric": "euclidean",
      "metric_kwds": null,
      "min_dist": 0.1,
      "n_components": 2,
      "n_epochs": null,
      "n_jobs": 1,
      "n_neighbors": 15,
      "negative_sample_rate": 5,
      "output_dens": false,
      "output_metric": "euclidean",
      "output_metric_kwds": null,
      "precomputed_knn": [
        null,
        null,
        null
      ],
      "random_state": 42,
      "repulsion_strength": 1.0,
      "set_op_mix_ratio": 1.0,
      "spread": 1.0,
      "target_metric": "categorical",
      "target_metric_kwds": null,
      "target_n_neighbors": -1,
      "target_weight": 0.5,
      "tqdm_kwds": {
        "desc": "Epochs completed",
        "bar_format": "{desc}: {percentage:3.0f}%| {bar} {n_fmt}/{total_fmt} [{elapsed}]",
        "disable": true
      },
      "transform_mode": "embedding",
      "transform_queue_size": 4.0,
      "transform_seed": 42,
      "unique": false,
      "verbose": false
    },
    "kmeans": {
      "algorithm": "lloyd",
      "copy_x": true,
      "init": "k-means++",
      "max_iter": 300,
      "n_clusters": 3,
      "n_init": 20,
      "random_state": 42,
      "tol": 0.0001,
      "verbose": 0
    }
  },
  "centroides": [
    [
      -3.90009112755458,
      14.52843521436055
    ],
    [
      12.600575424904049,
      1.268248857037959
    ],
    [
      5.2667760467529305,
      13.016412696838378
    ]
  ]
}
```
