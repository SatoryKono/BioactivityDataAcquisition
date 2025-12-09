"""Golden snapshot for activity_chembl pipeline outputs."""

from pathlib import Path

from .test_pipeline_outputs_helpers import load_expected_records

expected_activity_records = load_expected_records(
    Path("qc/golden/chembl_activity/expected_output.csv"),
    sort_key="activity_id",
)

__all__ = ["expected_activity_records"]
