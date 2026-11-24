"""Cálculos auditables y exportación de la defensa técnica."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

import pandas as pd

from config import CONFIG, CSV_COLUMNS, GATEWAYS, PROFILES
if TYPE_CHECKING:
    from pipeline import StreamingExperiment
    from review import ReviewedRun


def comparison_table(events: pd.DataFrame) -> pd.DataFrame:
    """Cada mitad: 1500 minutos por pasarela, no 3000 minutos."""
    if events.empty:
        return pd.DataFrame()
    data = events.copy()
    data["mitad"] = data["id"].apply(
        lambda i: "Antes (1–3000)" if i <= CONFIG.change_event else "Después (3001–6000)"
    )
    groups = data.groupby(["pasarela", "mitad"], observed=True, sort=False)
    stats = groups.agg(
        minutos=("id", "count"),
        fallos_medios=("fallos", "mean"),
        cuentas_medias=("cuentas", "mean"),
        ips_medias=("ips_origen", "mean"),
        fallos_totales=("fallos", "sum"),
    ).reset_index()
    if "cluster" in data.columns:
        for cluster in range(3):
            percentages = groups["cluster"].apply(lambda series: 100 * (series == cluster).mean())
            stats[f"porcentaje_grupo_{cluster}"] = [
                float(percentages.loc[(gateway, half)])
                for gateway, half in zip(stats.pasarela, stats.mitad, strict=True)
            ]
    if "perfil" in data.columns:
        for profile in PROFILES:
            pct_profile = groups["perfil"].apply(lambda series: 100 * (series == profile).mean())
            stats[f"porcentaje_{profile}"] = [
                float(pct_profile.loc[(gateway, half)])
                for gateway, half in zip(stats.pasarela, stats.mitad, strict=True)
            ]
        pct = groups["perfil"].apply(lambda series: 100 * (series == "fallos_repartidos").mean())
        stats["pct_perfil_repartido"] = [
            float(pct.loc[(gateway, half)])
            for gateway, half in zip(stats.pasarela, stats.mitad, strict=True)
        ]
    return stats.sort_values(["pasarela", "mitad"], key=lambda c: c.map({
        "Ámbar": 0, "Cobalto": 1,
        "Antes (1–3000)": 0, "Después (3001–6000)": 1,
    }) if c.name in ("pasarela", "mitad") else c).reset_index(drop=True)


def cluster_characterization(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "cluster" not in events.columns:
        return pd.DataFrame(), pd.DataFrame()
    char = events.groupby("cluster", sort=True).agg(
        eventos=("id", "size"),
        accesos_medios=("accesos_correctos", "mean"),
        fallos_medios=("fallos", "mean"),
        cuentas_medias=("cuentas", "mean"),
        ips_medias=("ips_origen", "mean"),
    ).reset_index()
    cross = pd.crosstab(events["cluster"], events["perfil"], normalize="index").reindex(columns=PROFILES, fill_value=0).mul(100)
    # No se fuerza una biyección entre los tres grupos y los tres perfiles.
    char["interpretacion"] = [
        f"Predominio {cross.loc[c].idxmax().replace('_', ' ')} ({cross.loc[c].max():.1f} %)"
        for c in char.cluster
    ]
    return char, cross


def morris_metrics(exact: int, estimate: float) -> dict[str, float]:
    signed = estimate - exact
    return {"exacto_csv": exact, "estimacion_morris": estimate, "diferencia_con_signo": signed,
            "error_absoluto": abs(signed), "error_relativo_porcentaje": 100 * abs(signed) / exact if exact else 0.0}


def metric_changes(stats: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for gateway in GATEWAYS:
        part = stats[stats.pasarela == gateway].set_index("mitad")
        if len(part) != 2:
            continue
        for metric in ("fallos_medios", "cuentas_medias", "ips_medias"):
            before, after = (float(part.loc[side, metric]) for side in ("Antes (1–3000)", "Después (3001–6000)"))
            rows.append({"pasarela": gateway, "metrica": metric, "antes": before, "despues": after,
                         "diferencia": after-before, "variacion_porcentaje": 100*(after-before)/before if before else None})
    return pd.DataFrame(rows)


def interpretation(stats: pd.DataFrame) -> str:
    if len(stats) != 4 or not stats.minutos.eq(1500).all():
        return "Comparación pendiente: se requieren 1.500 resúmenes por pasarela y mitad."
    changes = metric_changes(stats).set_index(["pasarela", "metrica"])
    c = changes.loc[("Cobalto", "cuentas_medias")]
    a = changes.loc[("Ámbar", "cuentas_medias")]
    f = changes.loc[("Cobalto", "fallos_medios")]
    af = changes.loc[("Ámbar", "fallos_medios")]
    return (f"Cobalto: cuentas de {c.antes:.3f} a {c.despues:.3f}/min "
            f"({c.diferencia:+.3f}; {c.variacion_porcentaje:+.2f} %). "
            f"Ámbar: {a.diferencia:+.3f} cuentas/min. Diferencia en diferencias: "
            f"{c.diferencia-a.diferencia:+.3f} cuentas/min. Los fallos cambian "
            f"{f.diferencia:+.3f}/min en Cobalto y {af.diferencia:+.3f}/min en Ámbar "
            f"(diferencia en diferencias: {f.diferencia-af.diferencia:+.3f}). "
            "El diseño conserva la esperanza de fallos (32,8/min) al cambiar el alcance; "
            "el recuento de fallos por sí solo no identifica ese mecanismo. "
            "Las cuentas son distintas por minuto; no representan personas únicas del periodo.")


def calculate_defense(exp: StreamingExperiment | ReviewedRun) -> dict[str, Any]:
    """Fuente exacta: CSV escritos en disco, no el contador in-memory."""
    csv_data = exp.from_csv()
    if not exp.is_finished or len(csv_data) != CONFIG.total_events:
        raise ValueError("La defensa final requiere 6000 registros procesados")
    derived = exp.snapshot()
    stats = comparison_table(derived)
    if len(stats) != 4 or not stats.minutos.eq(1500).all():
        raise ValueError("La defensa requiere 1500 resúmenes por pasarela y mitad")
    pd.testing.assert_frame_equal(csv_data[list(CSV_COLUMNS)], derived[list(CSV_COLUMNS)], check_dtype=False)
    clusters, cross = cluster_characterization(derived)

    morris: dict[str, dict[str, Any]] = {}
    for gateway in GATEWAYS:
        exact = int(csv_data.loc[csv_data.pasarela == gateway, "fallos"].sum())
        estimate = float(exp.morris.estimate(gateway))
        morris[gateway] = {
            **morris_metrics(exact, estimate),
            "registros_finales": exp.morris.counters[gateway].registers[:],
        }

    values: dict[str, dict[str, dict[str, float]]] = {}
    for gateway in GATEWAYS:
        values[gateway] = {}
        for side in ("Antes (1–3000)", "Después (3001–6000)"):
            row = stats[(stats.pasarela == gateway) & (stats.mitad == side)].iloc[0]
            values[gateway][side] = {
                "minutos": int(row.minutos),
                "fallos_medios": float(row.fallos_medios),
                "cuentas_medias": float(row.cuentas_medias),
                "ips_medias": float(row.ips_medias),
                "pct_perfil_repartido": float(row.pct_perfil_repartido),
                **{f"porcentaje_{p}": float(row[f"porcentaje_{p}"]) for p in PROFILES},
                **({f"grupo_{n}_porcentaje": float(row[f"porcentaje_grupo_{n}"])
                   for n in range(3)} if "cluster" in derived.columns else {}),
            }

    def delta(metric: str, gateway: str) -> float:
        return (
            values[gateway]["Después (3001–6000)"][metric]
            - values[gateway]["Antes (1–3000)"][metric]
        )

    return {
        "configuracion": {
            "semilla_simulacion": CONFIG.simulator_seed,
            "semilla_morris": CONFIG.morris_seed,
            "semilla_umap": CONFIG.umap_seed,
            "semilla_kmeans": CONFIG.kmeans_seed,
            "eventos": CONFIG.total_events,
            "minutos_por_pasarela": CONFIG.total_events // 2,
            "punto_de_cambio_id": CONFIG.change_event,
            "entrenamiento_global": CONFIG.initial_training_events,
        },
        "morris": morris,
        "mitades": values,
        "cambios": {
            g: {metric: delta(metric, g) for metric in ("fallos_medios", "cuentas_medias", "ips_medias", "pct_perfil_repartido")}
            for g in GATEWAYS
        },
        "diferencia_en_diferencias": {
            metric: delta(metric, "Cobalto") - delta(metric, "Ámbar")
            for metric in ("fallos_medios", "cuentas_medias", "ips_medias")
        },
        "clusters": clusters.to_dict(orient="records"),
        "pureza_por_cluster_porcentaje": (
            {str(i): {p: round(float(v), 4) for p,v in r.items()}
             for i,r in cross.to_dict(orient="index").items()} if not cross.empty else {}
        ),
        "umap_ejecutado": exp.ml_real,
        "proyeccion_disponible": bool(not clusters.empty),
        "modelos": exp.model_metadata,
        "variaciones": metric_changes(stats).to_dict(orient="records"),
        "interpretacion": interpretation(stats),
        "deteccion": exp.detector.summary(),
    }


def report_markdown(data: dict[str, Any]) -> str:
    before = "Antes (1–3000)"
    after = "Después (3001–6000)"
    change = data["cambios"]
    did = data["diferencia_en_diferencias"]
    lines = [
        "# Defensa técnica y conclusiones — Ciberseguridad en tiempo real",
        "",
        "**Trabajo final · Computación Masiva para Big Data**",
        "",
        "## 1. Arquitectura y trazabilidad",
        "",
        "El simulador crea 6.000 eventos (3.000 por pasarela), dos por minuto con un mismo instante: ",
        "Ámbar recibe los IDs impares y Cobalto los pares. Los CSV se escriben incrementalmente ",
        "desde el primer evento. La semilla de simulación es 42; el contador Morris utiliza una ",
        "fuente aleatoria diferente (semilla 420042, ramificada por pasarela).",
        "",
        "Las cuatro entradas de UMAP son accesos correctos, fallos, cuentas e IP de origen. ",
        "El escalador y la proyección se ajustan exclusivamente con los primeros 300 eventos ",
        "globales. K-means (k=3) se entrena sobre esa proyección; después solo se aplican ",
        "StandardScaler.transform, UMAP.transform y KMeans.predict.",
        "",
        "## 2. Cuantificación del error de Morris",
        "",
        "Cada fila representa un resumen por minuto, pero Morris procesa tantos incrementos ",
        "como intentos fallidos contenga la fila, para cada uno de los ocho registros.",
        "",
        "| Pasarela | Fallos exactos CSV | Morris (media de 8) | Diferencia firmada | Error absoluto | Error relativo |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for g in GATEWAYS:
        m = data["morris"][g]
        lines.append(
            f"| {g} | {m['exacto_csv']:,} | {m['estimacion_morris']:,.2f} | "
            f"{m['diferencia_con_signo']:+,.2f} | {m['error_absoluto']:,.2f} | "
            f"{m['error_relativo_porcentaje']:.2f} % |"
        )
    lines += [
        "",
        "Fórmulas: **error absoluto = |Morris − exacto|**; **error relativo = "
        "100 × error absoluto / exacto**.",
        "",
        "Registros finales (c₁,...,c₈): " + "; ".join(
            f"{g} = {data['morris'][g]['registros_finales']}" for g in GATEWAYS
        ) + ".",
        "",
        "## 3. Resultados antes y después",
        "",
        "Cada periodo contiene **1.500 resúmenes por pasarela**, equivalentes a 1.500 minutos.",
        "",
        "| Pasarela / periodo | Fallos medios/min | Cuentas medias/min | IP medias/min | Perfil repartido (%) |",
        "|---|---:|---:|---:|---:|",
    ]
    for g in GATEWAYS:
        for side in (before, after):
            v = data["mitades"][g][side]
            lines.append(
                f"| {g} — {'antes' if side==before else 'después'} | {v['fallos_medios']:.3f} | "
                f"{v['cuentas_medias']:.3f} | {v['ips_medias']:.3f} | "
                f"{v['pct_perfil_repartido']:.2f} |"
            )
    lines += [
        "",
        "### Cambios observados (segunda mitad − primera mitad)",
        "",
        f"- **Cobalto:** cuentas **{change['Cobalto']['cuentas_medias']:+.3f} cuentas/min**, "
        f"fallos **{change['Cobalto']['fallos_medios']:+.3f} fallos/min**, "
        f"IP **{change['Cobalto']['ips_medias']:+.3f} IP/min**.",
        f"- **Ámbar (control):** cuentas **{change['Ámbar']['cuentas_medias']:+.3f} cuentas/min**, "
        f"fallos **{change['Ámbar']['fallos_medios']:+.3f} fallos/min**, "
        f"IP **{change['Ámbar']['ips_medias']:+.3f} IP/min**.",
        f"- **Diferencia en diferencias (Cobalto − Ámbar):** "
        f"{did['cuentas_medias']:+.3f} cuentas/min; {did['fallos_medios']:+.3f} fallos/min.",
        "",
        "## 4. ¿Habría bastado observar únicamente los fallos?",
        "",
        "**No de forma fiable.** Los dos perfiles con muchos fallos comparten el intervalo "
        "30–50. Al cambiar su mezcla de 70 % concentrados / 10 % repartidos a "
        "10 % concentrados / 70 % repartidos, la cantidad **esperada** de fallos "
        "permanece constante. No obstante, crecen las cuentas e IP de origen afectadas. "
        "Cualquier variación pequeña de la media de fallos observada en la muestra responde "
        "a fluctuaciones aleatorias, no al mecanismo del cambio programado. "
        "Ámbar permanece con la distribución original y actúa como pasarela de control.",
        "",
        "No se deben sumar cuentas distintas por minuto para obtener cuentas únicas en todo el "
        "periodo: una misma cuenta podría aparecer en varios resúmenes. Tampoco se afirma "
        "que un grupo K-means confirme por sí solo un ataque real; faltaría investigar logs originales.",
        "",
        "## 5. UMAP y caracterización de K-means",
        "",
    ]
    if data["umap_ejecutado"]:
        lines += [
            "Los números de grupo (0, 1 y 2) son etiquetas arbitrarias. Se interpretan por las "
            "medias de accesos correctos, fallos, cuentas e IP, y se contrastan con los "
            "perfiles reales de simulación.",
            "",
            "| Grupo | Eventos | Fallos/min | Cuentas/min | IP/min | Interpretación |",
            "|---|---:|---:|---:|---:|---|",
        ]
        for c in data["clusters"]:
            lines.append(
                f"| {c['cluster']} | {c['eventos']} | {c['fallos_medios']:.2f} | "
                f"{c['cuentas_medias']:.2f} | {c['ips_medias']:.2f} | {c['interpretacion']} |"
            )
        lines += ["", "**Porcentaje de pertenencia a cada grupo por mitad:**", ""]
        lines += [
            "| Pasarela / mitad | Grupo 0 (%) | Grupo 1 (%) | Grupo 2 (%) |",
            "|---|---:|---:|---:|",
        ]
        for g in GATEWAYS:
            for side in (before,after):
                v = data["mitades"][g][side]
                lines.append(
                    f"| {g} — {'antes' if side==before else 'después'} | "
                    f"{v['grupo_0_porcentaje']:.2f} | {v['grupo_1_porcentaje']:.2f} | "
                    f"{v['grupo_2_porcentaje']:.2f} |"
                )
        lines += [
            "", "La composición de cada grupo por perfil real está guardada también en "
            "`resumen_defensa.json`, sección `pureza_por_cluster_porcentaje`. "
            "Esa comparación sirve para validar la interpretación, no para entrenar los grupos.",
        ]
    else:
        lines += [
            "**Pendiente de ejecutar en un entorno con `umap-learn`:** los CSV y Morris sí "
            "se calcularon de forma real. Para obtener las etiquetas y porcentajes de K-means "
            "sobre UMAP, instala las dependencias y ejecuta `python run_experiment.py`. "
            "Los valores de grupo no se han inventado ni sustituido por PCA/t-SNE.",
        ]
    lines += [
        "",
        "## 6. Reproducibilidad y limitaciones",
        "",
        "- La fecha inicial simulada es el 10/11/2026 a las 08:00; el periodo comprende 3.000 minutos.",
        "- Los intervalos de enteros incluyen ambos extremos.",
        "- La semilla 42 fija perfiles y medidas; las otras semillas fijan los algoritmos aleatorios.",
        "- Se preserva el mismo escalador, UMAP y K-means después del evento 300.",
        "- La semilla no hace iguales los resultados entre versiones diferentes de las dependencias: "
        "se aconseja conservar un entorno virtual estable.",
        "- La estimación Morris es aleatoria; aunque con ocho registros mejora respecto a una "
        "única copia, no debe presentarse como recuento exacto.",
        "",
        "**Referencia de requisitos:** `Trabajo_5.pdf` aportado en el enunciado.",
        "",
    ]
    lines += ["## 7. Interpretación calculada", "", data["interpretacion"], "",
              "## 8. Detección exploratoria causal", "", "```json",
              json.dumps(data["deteccion"], indent=2, ensure_ascii=False), "```", "",
              "Referencia fijada con observaciones iniciales; sin usar perfiles ni el ID del cambio. "
              "Las ventanas se solapan y su persistencia no equivale a pruebas estadísticas independientes.", "",
              "## 9. Modelos y reproducibilidad", "", "```json",
              json.dumps(data["modelos"], indent=2, ensure_ascii=False), "```", ""]
    return "\n".join(lines)


def export_defense(exp: StreamingExperiment, data: dict[str, Any] | None = None) -> tuple[Path, Path]:
    data = calculate_defense(exp) if data is None else data
    directory = exp.paths.results
    text_path = directory / "DEFENSA_TECNICA.md"
    json_path = directory / "resumen_defensa.json"
    text_path.write_text(report_markdown(data), encoding="utf-8")
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return text_path, json_path
