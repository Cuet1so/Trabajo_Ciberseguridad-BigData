import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from analytics import FixedUMAPClusters
from pipeline import StreamingExperiment
from playback import PlaybackClock
from review import ReviewedRun
from simulator import generate_events
from storage import check_manifest, RunPaths, digest
from tests.test_morris_pipeline import StubProjector


def test_playback_speed_pause_and_repeated_tick_preserve_data(tmp_path):
    outputs = []
    for i, interval in enumerate((.1, 5.0)):
        with StreamingExperiment(tmp_path/str(i), projector=StubProjector()) as exp:
            clock = PlaybackClock()
            clock.set_interval(interval, 0)
            clock.resume(0)
            assert clock.tick(exp, 0) == 0
            assert clock.tick(exp, interval) == 300
            assert clock.tick(exp, interval) == 0
            clock.pause()
            assert clock.tick(exp, interval*2) == 0
            clock.resume(interval*2)
            assert clock.tick(exp, interval*3+.001) == 100
            assert exp.event_count == 400
            outputs.append(exp.snapshot())
    assert outputs[0].equals(outputs[1])


def test_individual_steps_still_fit_and_transform_at_official_boundaries(tmp_path):
    model = StubProjector()
    with StreamingExperiment(tmp_path, projector=model) as exp:
        for i in range(300):
            exp.step(1)
            if i < 299:
                assert not model.fit_ids
        assert model.fit_ids == list(range(1, 301))
        for i in range(100):
            exp.step(1)
        assert model.future_ids == list(range(301, 401))
        assert [r["eventos"] for r in exp.history] == [300, 400]
        exp.step(6000)
        assert exp.event_count == 500


def test_active_writer_blocks_overwrite_and_restart_archives(tmp_path):
    with StreamingExperiment(tmp_path, use_ml=False) as first:
        first.step()
        before = (first.paths.data/"ambar.csv").read_bytes()
        with pytest.raises(RuntimeError, match="ocupada"):
            StreamingExperiment(tmp_path, use_ml=False)
        assert (first.paths.data/"ambar.csv").read_bytes() == before
    with StreamingExperiment(tmp_path, use_ml=False) as second:
        assert second.event_count == 0
        archive = list((tmp_path/"historial").glob("*/datos/ambar.csv"))
        assert len(archive) == 1 and archive[0].read_bytes() == before
        assert len(second.from_csv()) == 0


def test_review_does_not_generate_or_refit_and_models_can_be_reused(real_run, monkeypatch):
    exp, _ = real_run
    import simulator
    import pipeline
    def forbidden(*args, **kwargs):
        raise AssertionError("No se puede generar ni entrenar al revisar")
    monkeypatch.setattr(simulator, "generate_events", forbidden)
    monkeypatch.setattr(pipeline, "generate_events", forbidden)
    monkeypatch.setattr(FixedUMAPClusters, "fit_initial", forbidden)
    hashes = check_manifest(exp.paths)["sha256"].copy()
    review = ReviewedRun(exp.output_dir)
    assert review.event_count == 6000
    assert review.snapshot().cluster.equals(exp.snapshot().cluster)
    with pytest.raises(ValueError, match="confianza"):
        FixedUMAPClusters.load(exp.output_dir)
    loaded = FixedUMAPClusters.load(exp.output_dir, trusted_local=True)
    # Reutilización real: mismo lote de 100, mismo entorno y orden.
    events = list(generate_events())[300:400]
    coords, labels = loaded.transform_new(events)
    np.testing.assert_allclose(coords, exp.snapshot().iloc[300:400][["umap_x", "umap_y"]], rtol=1e-6)
    np.testing.assert_array_equal(labels, exp.snapshot().cluster.iloc[300:400])
    assert check_manifest(exp.paths)["sha256"] == hashes


def test_review_rejects_corruption_before_deserializing(real_run, tmp_path):
    exp, _ = real_run
    for name in ("datos", "resultados", "modelos"):
        shutil.copytree(exp.output_dir/name, tmp_path/name)
    shutil.copy2(exp.paths.manifest, tmp_path/"ejecucion.json")
    with (tmp_path/"datos"/"ambar.csv").open("a") as handle:
        handle.write("\nCORRUPTO")
    with pytest.raises(ValueError, match="Integridad"):
        ReviewedRun(tmp_path)
    with pytest.raises(ValueError, match="Integridad"):
        FixedUMAPClusters.load(tmp_path, trusted_local=True)


def test_failure_stops_without_silently_skipping_batch(tmp_path):
    class BrokenProjector(StubProjector):
        def fit_initial(self, events):
            coords, labels = super().fit_initial(events)
            coords[0, 0] = np.nan
            return coords, labels
    exp = StreamingExperiment(tmp_path, projector=BrokenProjector())
    with pytest.raises(ValueError, match="inválidas"):
        exp.step()
    with pytest.raises(RuntimeError, match="falló"):
        exp.step()
    assert exp.event_count == 300
    assert len(exp.from_csv()) == 300
    assert not exp.finalized
