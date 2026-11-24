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
    parser.add_argument("--screenshots", type=Path, default=Path("docs/capturas_ui"))
    args = parser.parse_args()
    args.screenshots.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, object] = {}
    with sync_playwright() as browser_api:
        browser = browser_api.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(args.url)
        assert response and response.status == 200
        expect(page.get_by_role("tab").first).to_be_visible(timeout=60000)
        expect(page.get_by_text("97.440", exact=True)).to_be_visible()
        expect(page.get_by_text("98.206", exact=True)).to_be_visible()
        for i, name in enumerate(("Fallos y Morris", "Mapa UMAP y grupos", "Antes y después"), 1):
            page.get_by_role("tab", name=name).click()
            page.locator(".js-plotly-plot:visible").first.wait_for(state="visible", timeout=30000)
            page.get_by_role("button", name="Stop", exact=True).wait_for(state="hidden", timeout=30000)
            page.get_by_test_id("stMain").evaluate("element => element.scrollTo(0, 0)")
            page.screenshot(path=str(args.screenshots/f"vista_{i}.png"), full_page=True)
            page.get_by_role("tabpanel").evaluate("""panel => {
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
        for label in ("CSV Ámbar", "CSV Cobalto", "Informe PDF"):
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
            expect(page.get_by_text("97.440", exact=True)).to_be_attached()
            evidence["simulacion"] = "Generación real desde 1 hasta 6000, primera vista 300, pausa, rerun, lote 400, reanudación y fin"
            evidence["ruta_simulacion"] = page.get_by_text("Ejecución local:", exact=False).inner_text()
            page.get_by_role("tab", name="Mapa UMAP y grupos").click()
            expect(page.get_by_text("6.000 puntos seleccionados de 6.000", exact=False)).to_be_visible()
            page.get_by_role("tab", name="Antes y después").click()
            expect(page.get_by_text("+13,981", exact=True).first).to_be_visible()
            page.get_by_text("Detección de cambios de comportamiento · análisis exploratorio", exact=True).click()
            page.screenshot(path=str(args.screenshots/"simulacion_final.png"), full_page=True)
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
        evidence["errores_javascript"] = errors
        assert not errors
        assert page.get_by_test_id("stException").count() == 0
        browser.close()
    Path("docs/navegador_ui.json" if args.simulate else "docs/navegador_ui_revision.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
