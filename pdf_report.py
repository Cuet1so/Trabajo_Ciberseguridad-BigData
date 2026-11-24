"""Generación reproducible del informe de defensa a partir de métricas auditadas.

La opción ML puede estar pendiente si no hay umap-learn en el entorno; nunca
se fabrican grupos ni porcentajes de K-means en ese caso.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)
from reportlab.graphics.shapes import Drawing, Line, Rect, String

NAVY = HexColor("#11283D")
BLUE = HexColor("#2868A5")
AMBER = HexColor("#BD851A")
CYAN = HexColor("#1687B5")
MUTED = HexColor("#617184")
PALE = HexColor("#EFF4F8")
GRID = HexColor("#DCE4ED")
DARK = HexColor("#1C2835")


def _fonts() -> tuple[str, str]:
    # Fuentes distribuidas por ReportLab: mismas métricas en Windows/macOS/Linux.
    base = Path(reportlab.__file__).parent / "fonts"
    if "Study" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Study", str(base / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("StudyBold", str(base / "VeraBd.ttf")))
        pdfmetrics.registerFont(TTFont("StudyItalic", str(base / "VeraIt.ttf")))
        pdfmetrics.registerFont(TTFont("StudyBoldItalic", str(base / "VeraBI.ttf")))
        pdfmetrics.registerFontFamily("Study", normal="Study", bold="StudyBold", italic="StudyItalic", boldItalic="StudyBoldItalic")
    return "Study", "StudyBold"


def _table(data: list[list[object]], *, widths: list[float] | None = None, header: bool = True, font: str = "DejaVuStudy", font_bold: str = "DejaVuStudyBold") -> Table:
    wrapped = []
    for index, row in enumerate(data):
        is_header = header and index == 0
        style = ParagraphStyle("cell", fontName=font_bold if is_header else font,
                               fontSize=7.5 if is_header else 8.1, leading=11,
                               textColor=colors.white if is_header else DARK)
        wrapped.append([Paragraph(escape(str(value)), style) if isinstance(value, (str, int, float)) else value for value in row])
    t = Table(wrapped, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, GRID),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PALE]),
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 8.1),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), font_bold),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ])
    t.setStyle(TableStyle(style))
    return t


def _summary_chart(title: str, values: list[float], maximum: float, font: str, bold: str, width: float) -> Drawing:
    """Comparación visual de las cuatro medias: Á antes/después, C antes/después."""
    d = Drawing(width, 153)
    d.add(String(10, 139, title, fontName=bold, fontSize=9, fillColor=NAVY))
    d.add(Line(25, 38, width-5, 38, strokeColor=GRID, strokeWidth=.8))
    left=34
    group_width=(width-45)/4
    palette=(AMBER, AMBER, CYAN, CYAN)
    for idx, (v, col) in enumerate(zip(values,palette,strict=True)):
        x=left+idx*group_width
        bh=max(1.5,(v/maximum)*81)
        d.add(Rect(x,38,group_width*.50,bh,fillColor=col,strokeColor=None))
        d.add(String(x+group_width*.25,42+bh,f"{v:.2f}",fontName=font,fontSize=7,fillColor=DARK,textAnchor="middle"))
        d.add(String(x+group_width*.25,25,("Á 1ª","Á 2ª","C 1ª","C 2ª")[idx],fontName=font,fontSize=7,fillColor=MUTED,textAnchor="middle"))
    return d


def _page(canvas, doc):  # type: ignore[no-untyped-def]
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 1.30 * cm, w, 1.30 * cm, stroke=0, fill=1)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(colors.white)
    canvas.drawString(1.70 * cm, h - .78 * cm, "BIG DATA  /  CIBERSEGURIDAD EN TIEMPO REAL")
    canvas.setStrokeColor(GRID)
    canvas.line(1.70 * cm, 1.48 * cm, w - 1.70 * cm, 1.48 * cm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.70 * cm, 1.06 * cm, "Simulación reproducible · semilla 42 · datos sintéticos")
    canvas.drawRightString(w - 1.70 * cm, 1.06 * cm, str(doc.page))
    canvas.restoreState()


def build_defense_pdf(summary: dict[str, Any], destination: Path) -> Path:
    """Construye el PDF a partir de calculate_defense(), sin estimaciones manuales."""
    regular, bold = _fonts()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitleCustom", fontName=bold, fontSize=21, leading=27, textColor=NAVY, spaceAfter=12))
    styles.add(ParagraphStyle(name="ReportSubtitleCustom", fontName=regular, fontSize=10, leading=15, textColor=MUTED, spaceAfter=18))
    styles.add(ParagraphStyle(name="ReportHeadingCustom", fontName=bold, fontSize=12, leading=16, textColor=NAVY, spaceBefore=12, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name="ReportTextCustom", fontName=regular, fontSize=9.1, leading=15.2, textColor=DARK, spaceAfter=10))
    styles.add(ParagraphStyle(name="ReportSmallCustom", fontName=regular, fontSize=8.1, leading=13, textColor=MUTED, spaceAfter=8))
    styles.add(ParagraphStyle(name="ReportMetricCustom", fontName=bold, fontSize=16, leading=20, alignment=TA_CENTER, textColor=NAVY))
    styles.add(ParagraphStyle(name="ReportCardLabelCustom", fontName=regular, fontSize=7.4, leading=11, alignment=TA_CENTER, textColor=MUTED))
    styles.add(ParagraphStyle(name="ReportNoteCustom", fontName=regular, fontSize=8.5, leading=14, textColor=NAVY, spaceAfter=8))

    doc = SimpleDocTemplate(
        str(destination), pagesize=A4,
        leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.65 * cm, bottomMargin=1.85 * cm,
        title="Defensa técnica - Ciberseguridad en tiempo real",
        author="Proyecto universitario de Big Data",
    )
    width = A4[0] - 3.4 * cm
    P = lambda text, sty="ReportTextCustom": Paragraph(text, styles[sty])
    story: list[object] = []

    story.append(Spacer(1, 12))
    story.append(P("DEFENSA TÉCNICA Y CONCLUSIONES", "ReportTitleCustom"))
    story.append(P("Trabajo final · Computación Masiva para Big Data · Dos pasarelas de autenticación", "ReportSubtitleCustom"))
    story.append(HRFlowable(width="100%", thickness=1, color=GRID, spaceAfter=17))
    cards = [
        [P("6.000", "ReportMetricCustom"), P("3.000", "ReportMetricCustom"), P("300", "ReportMetricCustom")],
        [P("Eventos generados", "ReportCardLabelCustom"), P("Minutos simulados", "ReportCardLabelCustom"), P("Eventos de entrenamiento UMAP", "ReportCardLabelCustom")],
    ]
    t = Table(cards, colWidths=[width/3]*3)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),PALE), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,0),11), ("BOTTOMPADDING",(0,-1),(-1,-1),11),
    ]))
    story.extend([t, Spacer(1, 19)])

    story.append(P("1. Objetivo y diseño experimental", "ReportHeadingCustom"))
    story.append(P(
        "Detectar un cambio de patrón de autenticación que <b>no altera sustancialmente el número de fallos</b>, "
        "pero sí amplía el número de cuentas afectadas por minuto. Los 6.000 resúmenes son sintéticos; "
        "Ámbar actúa como control y Cobalto cambia su distribución al comenzar el ID 3.001."))
    story.append(_table([
        ["Etapa", "Implementación reproducible"],
        ["Generación", "ID 1-6.000; pares Ámbar/Cobalto cada minuto desde 10/11/2026, 08:00"],
        ["Distribución inicial", "20 % pocos; 70 % concentrados; 10 % repartidos"],
        ["Cambio en Cobalto", "20 % pocos; 10 % concentrados; 70 % repartidos"],
        ["Morris", "8 registros por pasarela; sorteos independientes de la simulación"],
        ["UMAP y K-means", "StandardScaler + UMAP 2D + 3 centroides: fit solo con ID 1-300"],
    ], widths=[4.2*cm, width-4.2*cm], font=regular, font_bold=bold))

    story.append(P("2. Error cuantificado del contador Morris", "ReportHeadingCustom"))
    story.append(P(
        "Cada resumen contiene <b>f</b> fallos y ejecuta f incrementos lógicos por registro. "
        "Cada registro c aumenta con probabilidad 2<super>-c</super>. "
        "La estimación final es la media de las ocho expresiones (2<super>c</super> - 1). "
        "El valor de referencia es la suma de <b>fallos</b> en cada CSV."))
    rows = [["Pasarela", "Exacto CSV", "Morris (8)", "Diferencia", "Error absoluto", "Error relativo"]]
    for gateway in ("Ámbar", "Cobalto"):
        x = summary["morris"][gateway]
        rows.append([gateway, f"{x['exacto_csv']:,.0f}", f"{x['estimacion_morris']:,.0f}", f"{x['diferencia_con_signo']:+,.0f}", f"{x['error_absoluto']:,.0f}", f"{x['error_relativo_porcentaje']:.2f} %"])
    story.append(_table(rows, widths=[width/6]*6,font=regular,font_bold=bold))
    story.append(Spacer(1, 6))
    story.append(P("Error absoluto = |estimación - exacto|. Error relativo = 100 × error absoluto / exacto.", "ReportSmallCustom"))
    for gateway, values in summary["morris"].items():
        registers = values["registros_finales"]
        story.append(P(f"{gateway}: registros {registers}; estimaciones individuales "
                       f"{[2**c-1 for c in registers]}. La estimación publicada es su media aritmética.", "ReportSmallCustom"))

    story.append(PageBreak())
    story.append(P("3. Comparación antes y después", "ReportHeadingCustom"))
    story.append(P(
        "Se comparan exactamente <b>1.500 resúmenes/minutos por pasarela en cada mitad</b>. "
        "Las cuentas y direcciones IP son valores distintos <i>por minuto</i>, no únicos de todo el periodo."))
    b = "Antes (1–3000)"; a = "Después (3001–6000)"
    comparison = [["Pasarela / mitad", "Fallos/min", "Cuentas/min", "IP/min", "Repartidos"]]
    for gateway in ("Ámbar", "Cobalto"):
        for part, alias in ((b,"antes"), (a,"después")):
            d = summary["mitades"][gateway][part]
            comparison.append([
                f"{gateway} · {alias}", f"{d['fallos_medios']:.3f}",
                f"{d['cuentas_medias']:.3f}", f"{d['ips_medias']:.3f}",
                f"{d['pct_perfil_repartido']:.2f} %",
            ])
    story.append(_table(comparison, widths=[4.5*cm,3.1*cm,3.1*cm,2.85*cm,width-13.55*cm],font=regular,font_bold=bold))
    story.append(Spacer(1, 14))
    changes = summary["cambios"]
    change_c = changes["Cobalto"]["cuentas_medias"]
    before = summary["mitades"]["Cobalto"][b]["cuentas_medias"]
    percent = 100*change_c/before
    kpis = [
        [P(f"{change_c:+.3f}", "ReportMetricCustom"), P(f"{percent:+.1f} %", "ReportMetricCustom"), P(f"{changes['Cobalto']['fallos_medios']:+.3f}", "ReportMetricCustom")],
        [P("Cuentas/min extra en Cobalto", "ReportCardLabelCustom"), P("Cambio relativo de cuentas", "ReportCardLabelCustom"), P("Variación de fallos/min en Cobalto", "ReportCardLabelCustom")],
    ]
    c = Table(kpis, colWidths=[width/3]*3)
    c.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE), ("TOPPADDING",(0,0),(-1,0),12), ("BOTTOMPADDING",(0,-1),(-1,-1),12)]))
    story.append(c)
    story.append(Spacer(1, 18))
    story.append(P("4. ¿Se habría detectado el cambio mirando solo los fallos?", "ReportHeadingCustom"))
    story.append(P(
        "<b>No de forma fiable.</b> Los perfiles «fallos concentrados» y «fallos repartidos» generan el mismo "
        "intervalo de 30 a 50 intentos fallidos, por lo que el cambio de mezcla conserva la esperanza "
        "del número de fallos. En la simulación, Cobalto pasa de "
        f"<b>{summary['mitades']['Cobalto'][b]['fallos_medios']:.3f}</b> a "
        f"<b>{summary['mitades']['Cobalto'][a]['fallos_medios']:.3f}</b> fallos/min; "
        "en contraste, sus cuentas crecen de "
        f"<b>{before:.3f}</b> a <b>{summary['mitades']['Cobalto'][a]['cuentas_medias']:.3f}</b> cuentas/min."))
    story.append(P(
        "Ámbar mantiene la distribución original y sus cuentas pasan de "
        f"{summary['mitades']['Ámbar'][b]['cuentas_medias']:.3f} a "
        f"{summary['mitades']['Ámbar'][a]['cuentas_medias']:.3f} por minuto. "
        "La diferencia-en-diferencias del alcance de Cobalto frente a Ámbar es "
        f"<b>{summary['diferencia_en_diferencias']['cuentas_medias']:+.3f} cuentas/min</b>."))
    story.append(P(
        "El aumento también aparece en las IP de origen, que pasan en Cobalto de "
        f"{summary['mitades']['Cobalto'][b]['ips_medias']:.3f} a "
        f"{summary['mitades']['Cobalto'][a]['ips_medias']:.3f} por minuto."))
    charts = []
    for metric, title, scale in (("cuentas_medias", "Cuentas afectadas / minuto", 21.0), ("fallos_medios", "Fallos / minuto", 45.0)):
        vals = [summary["mitades"][gw][part][metric] for gw in ("Ámbar", "Cobalto") for part in (b,a)]
        charts.append(_summary_chart(title, vals, scale, regular, bold, width/2 - 6))
    fig = Table([[charts[0], charts[1]]], colWidths=[width/2,width/2])
    fig.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0),
                             ("RIGHTPADDING",(0,0),(-1,-1),0)]))
    story.append(Spacer(1,14))
    story.append(fig)
    story.append(P("Comparación visual de las medias: Á = Ámbar; C = Cobalto; 1ª / 2ª = primera / segunda mitad.", "ReportSmallCustom"))

    story.append(PageBreak())
    story.append(P("5. Modelado, agrupamiento y validez", "ReportHeadingCustom"))
    story.append(P(
        "El escalador, el UMAP 2D y K-means se ajustan una sola vez sobre los primeros "
        "300 registros globales (150 de cada pasarela). Las cuatro variables numéricas de entrada "
        "son <b>accesos_correctos, fallos, cuentas e ips_origen</b>. El ID, pasarela y perfil simulado "
        "se excluyen del aprendizaje. Para el resto de eventos se utiliza exclusivamente "
        "<b>scaler.transform → UMAP.transform → KMeans.predict</b>."))
    if summary.get("umap_ejecutado"):
        story.append(P("Resultados reales de los tres grupos K-means", "ReportHeadingCustom"))
        clusters = [["Grupo", "N", "Fallos/min", "Cuentas/min", "IP/min", "Descripción"]]
        for row in summary["clusters"]:
            clusters.append([
                str(row["cluster"]), str(row["eventos"]), f"{row['fallos_medios']:.2f}",
                f"{row['cuentas_medias']:.2f}", f"{row['ips_medias']:.2f}", row["interpretacion"],
            ])
        story.append(_table(clusters, widths=[1.45*cm,1.45*cm,2.5*cm,2.5*cm,2.2*cm,width-10.1*cm],font=regular,font_bold=bold))
        story.append(Spacer(1, 11))
        gr = [["Pasarela / mitad", "Grupo 0", "Grupo 1", "Grupo 2"]]
        for gateway in ("Ámbar", "Cobalto"):
            for part, alias in ((b,"antes"), (a,"después")):
                values=summary["mitades"][gateway][part]
                gr.append([f"{gateway} · {alias}",*[f"{values[f'grupo_{i}_porcentaje']:.2f} %" for i in range(3)]])
        story.append(_table(gr, widths=[width*.4]+[width*.2]*3,font=regular,font_bold=bold))
        story.append(P("Los nombres de grupo son arbitrarios; se caracterizan con las medias y después se contrastan con los perfiles sorteados. El detalle está en resumen_defensa.json.", "ReportSmallCustom"))
    else:
        story.append(_table([
            ["Estado del análisis", "Comprobación"],
            ["CSV + Morris", "Ejecutados y contrastados: cifras reales del experimento"],
            ["UMAP + K-means", "No ejecutados con modelos reales en esta ejecución diagnóstica"],
            ["Reproducción completa", "pip install -r requirements.txt; python run_experiment.py"],
        ], widths=[4.7*cm,width-4.7*cm],font=regular,font_bold=bold))
        story.append(P(
            "No se sustituyen las coordenadas ni los grupos por PCA, t-SNE o valores inventados. "
            "Al ejecutar el programa completo con umap-learn instalado, este mismo PDF se regenera "
            "automáticamente e incluye las tablas de clústeres.", "ReportSmallCustom"))
    story.append(P("6. Alcance de los resultados y conclusión", "ReportHeadingCustom"))
    story.append(P(
        "Las ocho copias de Morris reducen la variabilidad, pero una sola ejecución puede tener "
        "un error relevante: en Cobalto fue del "
        f"<b>{summary['morris']['Cobalto']['error_relativo_porcentaje']:.2f} %</b>. "
        "Debe utilizarse el total exacto del CSV para auditar la precisión. "
        "El cambio en el alcance es evidente en cuentas e IP por minuto, aunque la tasa de fallos "
        "permanezca próxima. Ningún clúster, por sí solo, demuestra un incidente real: "
        "para ello habría que revisar eventos originales, identidades, IP y contexto de autenticación."))
    story.append(P("Reproducción: datos/ contiene los CSV originales; resultados/ conserva eventos proyectados, evolución, resumen JSON y este PDF; modelos/ conserva los tres ajustes. Todas las cifras se calculan a partir de la ejecución actual.","ReportSmallCustom"))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=GRID))
    story.append(P("Enunciado de referencia: «Ciberseguridad en tiempo real», Trabajo final de Computación Masiva para Big Data (PDF aportado).", "ReportSmallCustom"))

    story.append(PageBreak())
    story.append(P("7. Arquitectura y algoritmos", "ReportHeadingCustom"))
    story.append(P("Medidas de la simulación: sorteos uniformes enteros, extremos incluidos", "ReportSmallCustom"))
    story.append(_table([["Perfil", "Correctos", "Fallos", "Cuentas", "IP"],
                         ["Pocos fallos", "40–70", "2–6", "1–2", "1–2"],
                         ["Concentrados", "40–70", "30–50", "1–3", "1–3"],
                         ["Repartidos", "40–70", "30–50", "20–30", "8–16"]],
                        widths=[width*.3]+[width*.175]*4, font=regular, font_bold=bold))
    # Diagramas vectoriales: exportables sin servicios externos ni capturas web.
    def flow(labels: list[str]) -> Drawing:
        drawing = Drawing(width, 64)
        cell = width / len(labels)
        for i, label in enumerate(labels):
            x = i*cell
            drawing.add(Rect(x+2, 16, cell-13, 36, fillColor=PALE, strokeColor=GRID))
            drawing.add(String(x+(cell-10)/2, 31, label, textAnchor="middle", fontName=regular, fontSize=7.2, fillColor=NAVY))
            if i < len(labels)-1:
                drawing.add(Line(x+cell-10, 34, x+cell+1, 34, strokeColor=BLUE))
                drawing.add(Line(x+cell-3, 37, x+cell+1, 34, strokeColor=BLUE))
                drawing.add(Line(x+cell-3, 31, x+cell+1, 34, strokeColor=BLUE))
        return drawing
    story.append(flow(["simulator", "pipeline + CSV", "analytics / Morris", "report", "app / PDF"]))
    story.append(flow(["f fallos", "f sorteos por registro", "u < 2^(-c)", "media de 2^c - 1"]))
    story.append(flow(["4 medidas", "StandardScaler", "UMAP 2D", "K-means k=3"]))
    story.append(P("En ID 1-300: ajuste de scaler, UMAP y centroides. En ID 301-6000: "
                   "transformación con ambos ajustes conservados y asignación al centroide más cercano. "
                   "Morris y el detector reciben cada evento desde ID 1; las vistas se actualizan en 300, 400, ..., 6000."))
    if summary.get("modelos"):
        model = summary["modelos"]
        story.append(P(f"Eventos proyectados: {model['eventos_procesados']}; entrenamiento: "
                       f"{model['eventos_entrenamiento']}; transformados: {model['eventos_transformados']}. "
                       "El instante, ID, pasarela y perfil quedan excluidos del vector."))
        centers = [["Grupo", "Centro UMAP 1", "Centro UMAP 2"]]
        centers += [[i, f"{xy[0]:.6f}", f"{xy[1]:.6f}"] for i, xy in enumerate(model["centroides"])]
        story.append(_table(centers, widths=[width/3]*3, font=regular, font_bold=bold))
        story.append(P("Correspondencia observada: porcentaje del perfil dentro de cada grupo", "ReportHeadingCustom"))
        cross = [["Grupo", "Pocos", "Concentrados", "Repartidos"]]
        for group, values in summary["pureza_por_cluster_porcentaje"].items():
            cross.append([group, *[f"{values.get(p, 0):.2f} %" for p in ("pocos_fallos", "fallos_concentrados", "fallos_repartidos")]])
        story.append(_table(cross, widths=[width/4]*4, font=regular, font_bold=bold))
        params = model["parametros"]
        story.append(P(f"Semillas: {escape(str(model['semillas']))}. UMAP: vecinos={params['umap']['n_neighbors']}, "
                       f"min_dist={params['umap']['min_dist']}, métrica={params['umap']['metric']}, n_jobs=1; "
                       f"K-means: n_init={params['kmeans']['n_init']}. Los parámetros completos, ID 1-300 y versiones "
                       "se conservan en modelos/metadatos.json y resumen_defensa.json.", "ReportSmallCustom"))
        story.append(P(escape(str(model["versiones"])), "ReportSmallCustom"))
    story.append(P("8. Detección exploratoria y límites", "ReportHeadingCustom"))
    detection = summary.get("deteccion", {})
    cfg = detection.get("configuracion", {})
    if cfg:
        story.append(P(f"Ventana: {cfg['window']} resúmenes/pasarela; referencia: los primeros "
                       f"{cfg['baseline_events']} observados; evaluación cada {cfg['stride']} minutos con "
                       f"{cfg['persistence']} ventanas consecutivas. Se exige aumento de Cobalto de al menos "
                       f"max({cfg['min_increase']} cuentas/min, {100*cfg['relative_increase']:.0f} % de su referencia), "
                       f"y aumento respecto a Ámbar de {cfg['min_control_gap']} cuentas/min. "
                       "La primera ventana evaluable es posterior al periodo de referencia."))
        found = detection.get("primera_deteccion")
        if found:
            story.append(P(f"Primera detección: ID {found['id']}, instante {found['instante']}. "
                           f"Cobalto: {found['cuentas_Cobalto']:.3f} cuentas/min; referencia "
                           f"{found['referencia_cobalto']:.3f}; aumento {found['aumento_cobalto']:+.3f}; "
                           f"diferencia frente al control {found['diferencia_control']:+.3f} cuentas/min."))
        else:
            story.append(P("No se observó un cambio que cumpliese el criterio configurado."))
    story.append(P(summary.get("interpretacion", "")))
    story.append(P("El detector no usa datos futuros ni conoce el ID del cambio. Las ventanas se solapan: "
                   "la persistencia es una heurística, no una garantía de significación estadística. "
                   "La referencia podría contaminarse en datos reales; estos umbrales no están calibrados "
                   "con incidentes etiquetados. UMAP distorsiona distancias y sus ejes no tienen unidades físicas; "
                   "los centroides fijos no se adaptan a nuevos patrones. Morris tiene varianza elevada incluso con ocho registros. "
                   "Las semillas y versiones permiten repetir esta ejecución; no garantizan identidad binaria entre plataformas."))
    story.append(P("Cada técnica aporta una perspectiva: Morris estima volumen, UMAP representa relaciones "
                   "entre cuatro medidas y K-means resume patrones. La comparación temporal de cuentas e IP "
                   "muestra el alcance que el volumen de fallos no distingue. Investigar un incidente exige "
                   "evidencia adicional: estos datos son sintéticos."))
    doc.build(story,onFirstPage=_page,onLaterPages=_page)
    return destination


if __name__ == "__main__":
    import json
    import argparse
    from storage import RunPaths, check_manifest, seal_run
    parser = argparse.ArgumentParser(description="Regenerar el PDF de una ejecución local íntegra")
    parser.add_argument("--run-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = RunPaths(args.run_dir)
    metadata = check_manifest(paths)
    lock = paths.root / ".execution.lock"
    with lock.open("x", encoding="utf-8") as handle:
        handle.write("Regeneración del informe PDF")
    try:
        data = json.loads((paths.results / "resumen_defensa.json").read_text(encoding="utf-8"))
        print(build_defense_pdf(data, paths.results / "Informe_Defensa_Tecnica.pdf"))
        seal_run(paths, metadata)
    finally:
        lock.unlink()
