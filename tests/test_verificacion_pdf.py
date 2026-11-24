from pathlib import Path

from pdf_report import build_defense_pdf
from pipeline import StreamingExperiment
from report import calculate_defense
from verificar import validate


def test_validation_and_pdf_generation(tmp_path: Path):
    with StreamingExperiment(output_dir=tmp_path,use_ml=False) as exp:
        exp.run_to_end()
        summary=calculate_defense(exp)
        pdf=build_defense_pdf(summary,tmp_path / "informe.pdf")
        assert pdf.read_bytes().startswith(b"%PDF-")
        assert len(pdf.read_bytes()) > 10_000
        results=validate(tmp_path)
        assert results["eventos"]==6000
        assert results["proyeccion_disponible"] is False


def test_pdf_and_projection_contract_with_stub(tmp_path: Path):
    """Prueba de contrato, NO ejecución de UMAP: se usa un doble explícito."""
    import numpy as np

    class OnlyContractProjector:
        def fit_initial(self, events):
            arr=np.asarray([e.features() for e in events])
            return arr[:, :2], np.asarray([i % 3 for i in range(len(events))])

        def transform_new(self, events):
            arr=np.asarray([e.features() for e in events])
            return arr[:, :2], np.asarray([i % 3 for i in range(len(events))])

    with StreamingExperiment(output_dir=tmp_path, projector=OnlyContractProjector()) as exp:
        exp.run_to_end()
        assert validate(tmp_path)["proyeccion_disponible"]
        import pytest
        with pytest.raises(ValueError, match="reales"):
            validate(tmp_path, require_ml=True)
        summary=calculate_defense(exp)
        assert summary["umap_ejecutado"] is False  # Un doble nunca acredita UMAP real.
        assert summary["proyeccion_disponible"] is True
        pdf=build_defense_pdf(summary,tmp_path / "contract_report.pdf")
        assert pdf.read_bytes().startswith(b"%PDF-")
