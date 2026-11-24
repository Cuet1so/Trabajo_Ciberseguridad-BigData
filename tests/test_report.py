from pathlib import Path

from pipeline import StreamingExperiment
from report import calculate_defense, comparison_table


def test_defense_reproducible_without_umap(tmp_path: Path):
    with StreamingExperiment(output_dir=tmp_path, use_ml=False) as app:
        app.run_to_end()
        data = calculate_defense(app)
        assert data["morris"]["Ámbar"]["exacto_csv"] == 97440
        assert data["morris"]["Cobalto"]["exacto_csv"] == 98206
        assert data["morris"]["Ámbar"]["estimacion_morris"] == 98303
        assert data["morris"]["Cobalto"]["estimacion_morris"] == 81919
        assert abs(data["cambios"]["Cobalto"]["cuentas_medias"] - 13.951333333333334) < 1e-10
        assert data["umap_ejecutado"] is False
