"""Golden records snapshot for testitem_chembl."""

from pathlib import Path

from tests.golden.pipeline_outputs.test_pipeline_outputs_helpers import (
    load_expected_records,
)

expected_testitem_records = load_expected_records(
    Path("data/output/testitem/testitem.csv"), sort_key="molecule_chembl_id"
)

__all__ = ["expected_testitem_records"]
