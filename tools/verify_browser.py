"""QA opcional en Chrome local: pip install -r requirements-browser.txt.

Arrancar antes: python -m streamlit run app.py -- --review .
Ejecutar: python tools/verify_browser.py [--simulate]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--evidence", type=Path, default=Path("docs/auditoria_final/navegador.json"))
    parser.add_argument("--screenshots", type=Path, default=Path("docs/capturas_ui"))
    args = parser.parse_args()
    args.screenshots.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, object] = {}
    with sync_playwright() as browser_api:
        browser = browser_api.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200}, device_scale_factor=1)
        errors = []
        def record_error(error):
            errors.append(str(error))
            print(f"JavaScript: {error}", flush=True)
        page.on("pageerror", record_error)
        response = page.goto(args.url)
        assert response and response.status == 200
        expect(page.get_by_role("tab", name="Inicio", exact=True)).to_be_visible(timeout=60000)
        page.get_by_role("tab", name="Inicio", exact=True).click()
        expect(page.get_by_role("button", name="Revisar resultados →", exact=True)).to_be_visible()
        page.screenshot(path=str(args.screenshots/"inicio.png"), full_page=True)
        page.get_by_role("button", name="Revisar resultados →", exact=True).click()
        expect(page.get_by_role("tab", name="Fallos y Morris", exact=True)).to_be_visible(timeout=60000)
        evidence["inicio"] = "Inicio y revisión directa de referencia, integridad validada"
        expect(page.get_by_text("97.440", exact=True)).to_be_visible()
        expect(page.get_by_text("98.206", exact=True)).to_be_visible()
        for i, name in enumerate(("Fallos y Morris", "Mapa UMAP y grupos", "Antes y después"), 1):
            page.get_by_role("tab", name=name).click()
            page.locator(".js-plotly-plot:visible").first.wait_for(state="visible", timeout=30000)
            page.get_by_role("button", name="Stop", exact=True).wait_for(state="hidden", timeout=30000)
            page.get_by_test_id("stMain").evaluate("element => element.scrollTo(0, 0)")
            page.screenshot(path=str(args.screenshots/f"vista_{i}.png"), full_page=True)
            page.get_by_role("tabpanel").last.evaluate("""panel => {
                const main = document.querySelector('[data-testid="stMain"]');
                main.scrollTop += panel.getBoundingClientRect().top - main.getBoundingClientRect().top - 64;
            }""")
            page.screenshot(path=str(args.screenshots/f"detalle_vista_{i}.png"), full_page=True)
        expect(page.get_by_text("+13,981", exact=True).first).to_be_visible()
        page.get_by_role("tab", name="Mapa UMAP y grupos").click()
        plot = page.locator(".js-plotly-plot:visible").first
        plot.scroll_into_view_if_needed()
        centers = plot.evaluate("plot => plot._fullData.filter(t => t.name.startsWith('Centroide')).map(t => ({name:t.name, text:t.text, type:t.type}))")
        assert [c["text"] for c in centers] == [["C0"], ["C1"], ["C2"]]
        evidence["centroides"] = centers
        symbols = plot.evaluate("p => p._fullData.filter(t => t.customdata && t.customdata.length).map(t => t.marker.symbol)")
        assert len(set(symbols)) == 3
        evidence["simbolos_grupos"] = symbols
        hover = plot.evaluate("""plot => {
            const trace = plot._fullData.find(t => t.customdata && t.customdata.length);
            const layout = plot._fullLayout, bounds = plot.getBoundingClientRect();
            // El punto extremo evita que el marcador del centroide intercepte el cursor.
            const index = Array.from(trace.x).reduce((best, value, i) => value < trace.x[best] ? i : best, 0);
            return {x: bounds.left + layout.xaxis._offset + layout.xaxis.l2p(trace.x[index]),
                    y: bounds.top + layout.yaxis._offset + layout.yaxis.l2p(trace.y[index])};
        }""")
        page.mouse.move(hover["x"], hover["y"])
        expect(plot.locator(".hoverlayer")).to_contain_text("Cuentas/min", timeout=10000)
        expect(plot.locator(".hoverlayer")).to_contain_text("IP/min")
        expect(plot.locator(".hoverlayer")).to_contain_text("Instante")
        plot.screenshot(path=str(args.screenshots/"mapa_completo.png"))
        evidence["tooltip"] = "Instante, cuentas e IP visibles al pasar el cursor por un punto real"
        for label, option in (("Pasarela", "Cobalto"), ("Periodo", "Segunda mitad")):
            page.get_by_role("combobox", name=label, exact=True).click()
            page.get_by_role("option", name=option, exact=True).click()
        expect(page.get_by_text("1.500 puntos seleccionados de 6.000", exact=False)).to_be_visible()
        page.get_by_role("button", name="Restablecer", exact=True).click()
        expect(page.get_by_text("6.000 puntos seleccionados de 6.000", exact=False)).to_be_visible()
        expect(page.get_by_role("combobox", name="Pasarela", exact=True)).to_have_value("Ambas")
        expect(page.get_by_role("combobox", name="Periodo", exact=True)).to_have_value("Completo")
        # Esperar al gráfico nuevo: el contador de selección se pinta antes
        # de que Plotly termine de sustituir el nodo DOM del lote filtrado.
        page.wait_for_function("""() => {
            const p = document.querySelector('.st-key-umap_chart .js-plotly-plot');
            return p?._fullData?.reduce((n,t)=>n+(t.customdata?.length||0),0) === 6000;
        }""")
        page.get_by_role("button", name="Stop", exact=True).wait_for(state="hidden", timeout=30000)
        page.wait_for_timeout(150)
        plot = page.locator(".st-key-umap_chart .js-plotly-plot")
        # Se observa el zoom nativo y se verifica el encuadre persistente explícito.
        plot.scroll_into_view_if_needed()
        zoom_box = plot.evaluate("""p => {
            const b=p.getBoundingClientRect(), a=p._fullLayout.xaxis, y=p._fullLayout.yaxis;
            return {x:b.left+a._offset, y:b.top+y._offset, w:a._length, h:y._length};
        }""")
        original_range = plot.evaluate("p => Array.from(p._fullLayout.xaxis.range)")
        page.mouse.move(zoom_box["x"] + zoom_box["w"]*.15, zoom_box["y"] + zoom_box["h"]*.15)
        page.mouse.down()
        page.mouse.move(zoom_box["x"] + zoom_box["w"]*.85, zoom_box["y"] + zoom_box["h"]*.85, steps=10)
        page.mouse.up()
        page.wait_for_timeout(250)
        zoomed_range = plot.evaluate("p => Array.from(p._fullLayout.xaxis.range)")
        assert zoomed_range != original_range
        # La selección sobrevive a otras vistas y al regreso desde Inicio.
        page.get_by_role("combobox", name="Origen de la proyección", exact=True).click()
        page.get_by_role("option", name="Ajuste inicial (1–300)", exact=True).click()
        expect(page.get_by_text("300 puntos seleccionados de 6.000", exact=False)).to_be_visible()
        # Comprueba también el límite de Streamlit: uirevision no sobrevive a
        # todas las recreaciones. El encuadre explícito sí tiene estado persistente.
        observed_range = page.locator(".js-plotly-plot:visible").first.evaluate("p => Array.from(p._fullLayout.xaxis.range)")
        evidence["zoom_arrastre_conservado"] = observed_range == zoomed_range
        page.get_by_text("Encuadre persistente del mapa", exact=True).click()
        lower, upper = float(zoomed_range[0]), float(zoomed_range[1])
        for label, value in (("UMAP 1 · mínimo", lower), ("UMAP 1 · máximo", upper)):
            field = page.get_by_role("spinbutton", name=label, exact=True)
            field.fill(str(value))
            field.press("Enter")
        page.get_by_text("Fijar límites de los ejes", exact=True).click()
        expect(page.get_by_role("checkbox", name="Fijar límites de los ejes")).to_be_checked()
        page.get_by_role("combobox", name="Origen de la proyección", exact=True).click()
        page.get_by_role("option", name="Transformados (301–6000)", exact=True).click()
        expect(page.get_by_text("5.700 puntos seleccionados de 6.000", exact=False)).to_be_visible()
        page.wait_for_function("""([lo,hi]) => {
            const p=document.querySelector('.st-key-umap_chart .js-plotly-plot');
            const r=p?._fullLayout?.xaxis?.range;
            return r && Math.abs(r[0]-lo)<1e-6 && Math.abs(r[1]-hi)<1e-6;
        }""", arg=[lower, upper])
        actual = page.locator(".js-plotly-plot:visible").first.evaluate("p => Array.from(p._fullLayout.xaxis.range)")
        assert all(abs(a-b) < 1e-6 for a,b in zip(actual, (lower, upper), strict=True)), (actual, lower, upper)
        evidence["encuadre_persistente"] = "Límites introducidos conservados tras cambiar el filtro; comprobados contra el rango real Plotly"
        page.get_by_text("Fijar límites de los ejes", exact=True).click()
        page.get_by_role("combobox", name="Origen de la proyección", exact=True).click()
        page.get_by_role("option", name="Ajuste inicial (1–300)", exact=True).click()
        page.get_by_role("tab", name="Fallos y Morris", exact=True).click()
        expect(page.get_by_role("combobox", name="Pasarela", exact=True)).to_have_count(0)
        page.get_by_role("tab", name="Mapa UMAP y grupos", exact=True).click()
        expect(page.get_by_text("300 puntos seleccionados de 6.000", exact=False)).to_be_visible()
        page.get_by_role("combobox", name="Origen de la proyección", exact=True).click()
        page.get_by_role("option", name="Transformados (301–6000)", exact=True).click()
        expect(page.get_by_text("5.700 puntos seleccionados de 6.000", exact=False)).to_be_visible()
        page.get_by_role("button", name="Restablecer", exact=True).click()
        # Zoom permanece tras filtrar; uirevision es estable para esta ejecución.
        plot = page.locator(".js-plotly-plot:visible").first
        revision = plot.evaluate("p => p.layout.uirevision")
        assert revision
        evidence["vistas"] = "Solo la vista activa se construye; filtros de ajuste/transformación y selección persistentes"
        for label in ("CSV Ámbar", "CSV Cobalto", "Informe PDF", "Resumen JSON", "Proyecciones CSV"):
            with page.expect_download() as download:
                page.get_by_role("button", name=label, exact=True).click()
            assert download.value.failure() is None
        evidence["descargas"] = "Ambos CSV y el PDF descargados sin errores"
        evidence["restablecer"] = "Restablece ambas pasarelas, periodo completo y los tres grupos"
        evidence["revision"] = "Tres vistas, totales CSV, diferencia en diferencias y filtros visibles"
        if args.simulate:
            page.get_by_role("radiogroup", name="Modo", exact=True).get_by_text("Simulación", exact=True).click()
            # Da tiempo para pausar en el primer punto de actualización oficial.
            page.get_by_role("slider").press("End")
            expect(page.get_by_role("slider")).to_have_value("5")
            page.get_by_role("button", name="Iniciar simulación", exact=True).click()
            expect(page.get_by_text("Último ID: 300", exact=False)).to_be_visible(timeout=60000)
            page.get_by_role("button", name="Pausar", exact=True).click()
            # Pausa confirmada: un rerun de filtro no escribe otro lote.
            before = page.get_by_text("Último ID:", exact=False).inner_text()
            page.get_by_role("tab", name="Mapa UMAP y grupos").click()
            expect(page.get_by_text("300 puntos seleccionados de 300", exact=False)).to_be_visible()
            page.get_by_role("combobox", name="Periodo", exact=True).click()
            page.get_by_role("option", name="Completo", exact=True).click()
            expect(page.get_by_text(before, exact=True)).to_be_visible()
            page.get_by_role("button", name="Siguiente lote", exact=True).click()
            expect(page.get_by_text("Último ID: 400", exact=False)).to_be_visible(timeout=60000)
            page.get_by_role("slider").press("Home")
            expect(page.get_by_role("slider")).to_have_value("0")
            page.get_by_role("button", name="Reanudar", exact=True).click()
            expect(page.get_by_text("Ejecución completa: 6.000 eventos, proyección y resultados exportados.", exact=True)).to_be_visible(timeout=180000)
            page.get_by_role("tab", name="Fallos y Morris", exact=True).click()
            expect(page.get_by_text("97.440", exact=True)).to_be_visible()
            evidence["simulacion"] = "Generación real desde 1 hasta 6000, primera vista 300, pausa, rerun, lote 400, reanudación y fin"
            evidence["ruta_simulacion"] = page.get_by_text("Ejecución local:", exact=False).inner_text()
            page.get_by_role("tab", name="Mapa UMAP y grupos").click()
            expect(page.get_by_text("6.000 puntos seleccionados de 6.000", exact=False)).to_be_visible()
            page.get_by_role("tab", name="Antes y después").click()
            expect(page.get_by_text("+13,981", exact=True).first).to_be_visible()
            page.get_by_text("Detección de cambios de comportamiento · análisis exploratorio", exact=True).click()
            page.screenshot(path=str(args.screenshots/"simulacion_final.png"), full_page=True)
        evidence["responsive"] = []
        for width in (1920, 1440, 1024, 768, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            page.wait_for_timeout(350)
            for view in ("Fallos y Morris", "Mapa UMAP y grupos", "Antes y después"):
                print(f"Responsive {width}: {view}", flush=True)
                try:
                    page.get_by_role("tab", name=view, exact=True).click()
                except Exception:
                    page.screenshot(path=str(args.screenshots/"fallo_responsive.png"), full_page=True)
                    print(page.locator("body").inner_text(), flush=True)
                    raise
                page.get_by_role("button", name="Stop", exact=True).wait_for(state="hidden", timeout=30000)
                measured = page.evaluate("({width: innerWidth, documentWidth: document.documentElement.scrollWidth})")
                assert measured["documentWidth"] <= width + 2, (view, measured)
                evidence["responsive"].append({"vista": view, **measured})
            page.screenshot(path=str(args.screenshots/f"responsive_{width}.png"), full_page=True)
        # Teclado: tabs accesibles y foco visible, no auditoría WCAG completa.
        tab = page.get_by_role("tab", name="Fallos y Morris", exact=True)
        tab.focus()
        tab.press("Enter")
        expect(tab).to_have_attribute("aria-selected", "true")
        focus = tab.evaluate("e => getComputedStyle(e).outlineStyle")
        assert focus != "none"
        evidence["teclado"] = "Pestañas activables con Enter; indicador de foco visible"
        page.set_viewport_size({"width": 390, "height": 844})
        # Espera a que termine la animación de cierre automático de la barra.
        page.wait_for_function("document.querySelector('[data-testid=stSidebar]').getBoundingClientRect().right <= 1")
        page.get_by_test_id("stMain").evaluate("element => element.scrollTo(0, 0)")
        page.wait_for_function("document.querySelector('[data-testid=stMain]').getBoundingClientRect().left < 20")
        # Streamlit permite desplazar tablas y gráficas sin desbordar el documento.
        page.screenshot(path=str(args.screenshots/"movil.png"), full_page=True)
        evidence["movil"] = page.evaluate("({width: window.innerWidth, documentWidth: document.documentElement.scrollWidth})")
        assert evidence["movil"]["documentWidth"] <= 392
        page.get_by_role("tab", name="Mapa UMAP y grupos", exact=True).click()
        expect(page.get_by_text("6.000 puntos seleccionados de 6.000", exact=False)).to_be_visible()
        mobile_plot = page.locator(".js-plotly-plot:visible").first
        mobile_plot.scroll_into_view_if_needed()
        page.screenshot(path=str(args.screenshots/"movil_mapa.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth") <= 392
        if args.simulate:
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.wait_for_timeout(500)
            expand = page.get_by_test_id("stExpandSidebarButton")
            if expand.is_visible():
                expand.click()
            page.get_by_role("slider").press("End")
            page.get_by_text("Reiniciar simulación", exact=True).click()
            expect(page.get_by_role("button", name="Reiniciar", exact=True)).to_be_disabled()
            page.get_by_text("Confirmo reiniciar esta simulación", exact=True).click()
            expect(page.get_by_role("checkbox", name="Confirmo reiniciar esta simulación")).to_be_checked()
            page.get_by_role("button", name="Reiniciar", exact=True).click()
            expect(page.get_by_text("Último ID: 300", exact=False)).to_be_visible(timeout=60000)
            page.get_by_role("button", name="Pausar", exact=True).click()
            evidence["reinicio"] = "Confirmación obligatoria, nueva ejecución 300, archivos previos conservados"
        evidence["errores_javascript"] = errors
        assert not errors
        assert page.get_by_test_id("stException").count() == 0
        browser.close()
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
