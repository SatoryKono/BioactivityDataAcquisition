"""Golden snapshot for testitem_chembl pipeline outputs."""

from pathlib import Path

from .utils import load_expected_records

expected_testitem_records = load_expected_records(
    Path("data/output/testitem/testitem.csv"), sort_key="molecule_chembl_id"
)

__all__ = ["expected_testitem_records"]
