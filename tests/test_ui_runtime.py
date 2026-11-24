"""Un lector de la interfaz no puede observar un lote sin proyectar."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from pipeline import StreamingExperiment
from tests.test_morris_pipeline import StubProjector
from ui_runtime import serialized_ui_operation


def test_ui_serializes_processing_and_reads(tmp_path):
    fitting, finish, reader_started, reader_entered = (Event() for _ in range(4))

    class WaitingProjector(StubProjector):
        def fit_initial(self, events):
            fitting.set()
            assert finish.wait(5)
            return super().fit_initial(events)

    with StreamingExperiment(tmp_path, projector=WaitingProjector()) as exp:
        step = serialized_ui_operation(exp.step)

        @serialized_ui_operation
        def read():
            reader_entered.set()
            return exp.snapshot(), exp.from_csv()

        def request_read():
            reader_started.set()
            return read()

        with ThreadPoolExecutor(max_workers=2) as pool:
            writer = pool.submit(step)
            try:
                assert fitting.wait(5)
                reader = pool.submit(request_read)
                assert reader_started.wait(5)
                assert not reader_entered.wait(.05)
            finally:
                finish.set()
            assert writer.result(timeout=5) == 300
            points, raw = reader.result(timeout=5)
        assert reader_entered.is_set()
        assert len(points) == len(raw) == 300
        assert points.cluster.notna().all()
        assert points.id.tolist() == raw.id.tolist() == list(range(1, 301))
