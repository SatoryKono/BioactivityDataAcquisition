"""Golden records snapshot for molecule_chembl."""

from pathlib import Path

from tests.golden.pipeline_outputs.test_pipeline_outputs_helpers import (
    load_expected_records,
)

expected_molecule_records = load_expected_records(
    Path("data/output/molecule/molecule.csv"), sort_key="molecule_chembl_id"
)

__all__ = ["expected_molecule_records"]
