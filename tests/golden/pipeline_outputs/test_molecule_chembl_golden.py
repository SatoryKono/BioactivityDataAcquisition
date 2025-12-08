"""Golden snapshot for molecule_chembl pipeline outputs."""

from pathlib import Path

from .test_pipeline_outputs_helpers import load_expected_records

expected_molecule_records = load_expected_records(
    Path("data/output/molecule/molecule.csv"), sort_key="molecule_chembl_id"
)

__all__ = ["expected_molecule_records"]
