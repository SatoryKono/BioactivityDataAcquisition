"""Golden snapshot for assay_chembl pipeline outputs."""
from pathlib import Path

from .utils import load_expected_records

expected_assay_records = load_expected_records(
    Path("data/output/assay/assay.csv"), sort_key="assay_chembl_id"
)

__all__ = ["expected_assay_records"]
