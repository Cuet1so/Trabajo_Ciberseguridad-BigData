from pathlib import Path

from streamlit.testing.v1 import AppTest

from pipeline import StreamingExperiment
from tests.test_morris_pipeline import StubProjector


def test_real_dashboard_three_views_and_gateway_filter(real_run):
    exp, _ = real_run
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30)
    app.session_state["experiment"] = exp
    app.session_state["playing"] = False
    app.run()
    assert not app.exception
    assert len(app.tabs) == 3
    assert [m.value for m in app.metric if m.label == "Fallos exactos"] == ["97.440", "98.206"]
    assert "13,951" in " ".join(m.value for m in app.markdown)
    for gateway in ("Ámbar", "Cobalto", "Ambas"):
        app.selectbox(key="gateway_filter").set_value(gateway).run()
        assert not app.exception
        assert exp.event_count == 6000


def test_first_display_at_300_and_no_duplicate_rerun(tmp_path):
    with StreamingExperiment(tmp_path, projector=StubProjector()) as exp:
        app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30)
        app.session_state["experiment"] = exp
        app.session_state["playing"] = False
        app.run()
        assert len(app.tabs) == 0
        app.button(key="step").click().run()
        assert not app.exception
        assert exp.event_count == 300
        assert len(app.tabs) == 3
        snapshot = exp.from_csv().copy()
        cached = app.session_state["dashboard_snapshot"][1]
        app.run()
        assert exp.from_csv().equals(snapshot)
        app.button(key="step").click().run()
        assert exp.event_count == 400
        assert exp.from_csv().id.is_unique
        updated = app.session_state["dashboard_snapshot"][1]
        assert updated is not cached
        assert len(updated.points) == len(updated.raw) == 400


def test_filters_period_group_and_empty_selection(real_run):
    exp, _ = real_run
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30)
    app.session_state["experiment"] = exp
    app.run()
    from dashboard import filter_points
    for period in ("Primera mitad", "Segunda mitad", "Completo"):
        app.selectbox(key="period_filter").set_value(period).run()
        for gateway in ("Ámbar", "Cobalto", "Ambas"):
            app.selectbox(key="gateway_filter").set_value(gateway).run()
            app.multiselect(key="group_filter").set_value([2]).run()
            expected = filter_points(exp.snapshot(), gateway, period, [2])
            assert not app.exception
            assert any(f"{len(expected):,}".replace(",", ".") + " puntos seleccionados" in caption.value for caption in app.caption)
            assert expected.cluster.eq(2).all()
    app.multiselect(key="group_filter").set_value([]).run()
    assert not app.exception
    assert any("No hay eventos" in element.value for element in app.info)


def test_ui_start_pause_resume_speed_and_confirmed_reset(tmp_path, monkeypatch):
    import pipeline
    original = StreamingExperiment
    def engine(path, **kwargs):
        return original(path, projector=StubProjector(), **kwargs)
    monkeypatch.setattr(pipeline, "StreamingExperiment", engine)
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30)
    app.run()
    assert "experiment" not in app.session_state
    app.text_input(key="runs_directory").set_value(str(tmp_path)).run()
    app.button(key="start").click().run()
    assert not app.exception
    first = app.session_state["experiment"]
    assert first.event_count == 300
    assert app.multiselect(key="group_filter").value == [0, 1, 2]
    app.button(key="play").click().run()
    assert not app.session_state["clock"].playing
    frozen = first.from_csv()
    app.run()
    assert first.from_csv().equals(frozen)
    app.select_slider(key="speed").set_value(5.0).run()
    assert app.session_state["clock"].interval == 5.0
    app.button(key="play").click().run()
    assert app.session_state["clock"].playing
    assert first.event_count == 300
    app.button(key="play").click().run()
    assert app.button(key="reset").disabled
    app.checkbox(key="confirm_reset").check().run()
    assert not app.button(key="reset").disabled
    app.button(key="reset").click().run()
    assert not app.exception
    second = app.session_state["experiment"]
    assert second is not first and second.event_count == 300
    assert first.from_csv().equals(frozen)
    assert not app.session_state["confirm_reset"]
    second.close()


def test_ui_review_uses_same_figures_without_generator(real_run, monkeypatch):
    exp, _ = real_run
    import pipeline
    monkeypatch.setattr(pipeline, "StreamingExperiment", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("No generar")))
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30).run()
    app.radio(key="mode").set_value("Revisión").run()
    app.text_input(key="review_path").set_value(str(exp.output_dir)).run()
    app.button(key="load_review").click().run()
    assert not app.exception
    assert len(app.tabs) == 3
    assert app.session_state["reviewed"].summary["morris"]["Cobalto"]["exacto_csv"] == 98206
    assert [m.value for m in app.metric if m.label == "Fallos exactos"] == ["97.440", "98.206"]


def test_failed_run_rerun_stays_usable(tmp_path):
    import pytest
    class Failing(StubProjector):
        def fit_initial(self, events):
            raise RuntimeError("Error de modelo provocado para la prueba")
    exp = StreamingExperiment(tmp_path, projector=Failing())
    with pytest.raises(RuntimeError):
        exp.step()
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30)
    app.session_state["experiment"] = exp
    app.run()
    app.run()
    assert not app.exception
    assert any("Ejecución incompleta" in element.value for element in app.error)
    assert app.button(key="play").disabled
    assert app.button(key="step").disabled
    assert exp.event_count == 300 and len(exp.from_csv()) == 300


def test_ui_kpis_reset_filters_and_reuse_snapshot(real_run, monkeypatch):
    """Un cambio de filtros no vuelve a leer CSV ni a ejecutar el pipeline."""
    from bi_metrics import number
    exp, _ = real_run
    raw = exp.from_csv()
    reads = []
    original = exp.from_csv

    def counted_csv():
        reads.append(exp.event_count)
        return original()

    monkeypatch.setattr(exp, "from_csv", counted_csv)
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30)
    app.session_state["experiment"] = exp
    app.run()
    expected_accounts = raw.loc[(raw.pasarela == "Cobalto") & (raw.id > 3000), "cuentas"].mean()
    assert next(m.value for m in app.metric if m.label == "Cuentas en Cobalto") == number(expected_accounts, 2)
    cached = app.session_state["dashboard_snapshot"][1]
    app.selectbox(key="gateway_filter").set_value("Cobalto").run()
    app.selectbox(key="period_filter").set_value("Segunda mitad").run()
    app.multiselect(key="group_filter").set_value([2]).run()
    app.button(key="reset_filters").click().run()
    assert not app.exception
    assert app.selectbox(key="gateway_filter").value == "Ambas"
    assert app.selectbox(key="period_filter").value == "Completo"
    assert app.multiselect(key="group_filter").value == [0, 1, 2]
    assert any("6.000 puntos seleccionados" in caption.value for caption in app.caption)
    assert app.session_state["dashboard_snapshot"][1] is cached
    assert reads == [6000]
    assert exp.event_count == 6000
