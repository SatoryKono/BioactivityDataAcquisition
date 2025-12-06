"""Golden snapshot for target_chembl pipeline outputs."""

from pathlib import Path

from .utils import load_expected_records

expected_target_records = load_expected_records(
    Path("data/output/target/target.csv"), sort_key="target_chembl_id"
)

__all__ = ["expected_target_records"]
