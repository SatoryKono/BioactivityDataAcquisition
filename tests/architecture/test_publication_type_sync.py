"""Architecture test: verify CSV ↔ JSON classification asset sync.

Ensures the JSON asset matches the reference CSV file
configs/enums/publication_type_classification.csv.
"""

from __future__ import annotations

import pytest

import csv
import json
from pathlib import Path

pytestmark = pytest.mark.architecture

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_CSV_PATH = _PROJECT_ROOT / "configs" / "enums" / "publication_type_classification.csv"
_JSON_PATH = (
    _PROJECT_ROOT
    / "configs"
    / "enums"
    / "publication_type_classification.asset.v1.json"
)


def _load_json_rows() -> list[list[str]]:
    raw = json.loads(_JSON_PATH.read_text("utf-8"))
    return raw["rows"]


class TestClassificationCSVJsonSync:
    """Verify JSON asset matches reference CSV."""

    def test_csv_file_exists(self) -> None:
        assert _CSV_PATH.exists(), f"CSV not found: {_CSV_PATH}"

    def test_json_file_exists(self) -> None:
        assert _JSON_PATH.exists(), f"JSON not found: {_JSON_PATH}"

    def test_row_count_matches(self) -> None:
        with _CSV_PATH.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            csv_rows = list(reader)
        json_rows = _load_json_rows()
        assert len(csv_rows) == len(json_rows), (
            f"CSV has {len(csv_rows)} rows but JSON has {len(json_rows)}"
        )

    def test_unified_types_match(self) -> None:
        """Every unified_type in JSON matches the CSV."""
        with _CSV_PATH.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            csv_types = [row[1] for row in reader]
        json_types = [row[0] for row in _load_json_rows()]
        assert json_types == csv_types

    def test_class_codes_match(self) -> None:
        """Every class_code in JSON matches the CSV."""
        with _CSV_PATH.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            csv_codes = [row[3] for row in reader]
        json_codes = [row[2] for row in _load_json_rows()]
        assert json_codes == csv_codes

    def test_subclass_match(self) -> None:
        """Every subclass in JSON matches the CSV."""
        with _CSV_PATH.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            csv_subclasses = [row[2] for row in reader]
        json_subclasses = [row[1] for row in _load_json_rows()]
        assert json_subclasses == csv_subclasses
