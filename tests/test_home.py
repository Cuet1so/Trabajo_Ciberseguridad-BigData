from pathlib import Path
from streamlit.testing.v1 import AppTest
from pipeline import StreamingExperiment
from tests.test_morris_pipeline import StubProjector


def test_home_is_default_and_does_not_generate():
    app = AppTest.from_file(Path('app.py').resolve()).run()
    assert not app.exception
    assert app.session_state['navigation'] == 'Inicio'
    assert 'experiment' not in app.session_state
    assert any('Las cuentas revelan' in m.value for m in app.markdown)
    app.button(key='home_simulation').click().run()
    assert not app.exception
    assert app.session_state['navigation'] == 'Simulación'
    assert app.button(key='start')
    assert 'experiment' not in app.session_state


def test_return_home_pauses_and_preserves_progress(tmp_path):
    with StreamingExperiment(tmp_path, projector=StubProjector()) as exp:
        exp.step()
        app = AppTest.from_file(Path('app.py').resolve())
        app.session_state['experiment'] = exp
        app.run()
        original = exp.from_csv().copy()
        app.session_state['navigation'] = 'Inicio'
        app.run()
        assert not app.exception
        assert not app.session_state['clock'].playing
        app.button(key='home_simulation').click().run()
        assert not app.exception
        assert exp.event_count == 300
        assert original.equals(exp.from_csv())
        assert len(app.tabs) == 5


def test_reference_shortcut_validates_without_generating(monkeypatch):
    import pipeline
    def forbidden(*args, **kwargs):
        raise AssertionError("La revisión no genera eventos")
    monkeypatch.setattr(pipeline, "StreamingExperiment", forbidden)
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30).run()
    app.button(key="home_review").click().run()
    assert not app.exception
    assert app.radio(key="mode").value == "Revisión"
    assert app.session_state["reviewed"].event_count == 6000
    assert "experiment" not in app.session_state
    assert [m.value for m in app.metric if m.label == "Fallos exactos"] == ["97.440", "98.206"]
