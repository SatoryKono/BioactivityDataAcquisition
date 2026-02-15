"""Architecture test: verify CSV ↔ Python classification table sync.

Ensures the Python constant _CLASSIFICATION_TABLE matches the reference
CSV file configs/data_schema/publication_type_classification.csv.
"""

from __future__ import annotations

import csv
from pathlib import Path

from bioetl.domain.mapping.publication_type_classification import (
    CLASSIFICATION_TABLE_SIZE,
    _CLASSIFICATION_TABLE,
)

_CSV_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "schemas"
    / "publication_type_classification.csv"
)


class TestClassificationCSVSync:
    """Verify Python table matches reference CSV."""

    def test_csv_file_exists(self) -> None:
        assert _CSV_PATH.exists(), f"CSV not found: {_CSV_PATH}"

    def test_row_count_matches(self) -> None:
        with _CSV_PATH.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            csv_rows = list(reader)
        assert len(csv_rows) == CLASSIFICATION_TABLE_SIZE, (
            f"CSV has {len(csv_rows)} rows but Python table has "
            f"{CLASSIFICATION_TABLE_SIZE}"
        )

    def test_unified_types_match(self) -> None:
        """Every unified_type in Python table matches the CSV."""
        with _CSV_PATH.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            csv_types = [row[1] for row in reader]
        python_types = [row[0] for row in _CLASSIFICATION_TABLE]
        assert python_types == csv_types

    def test_class_codes_match(self) -> None:
        """Every class_code in Python table matches the CSV."""
        with _CSV_PATH.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            csv_codes = [row[3] for row in reader]
        python_codes = [row[2] for row in _CLASSIFICATION_TABLE]
        assert python_codes == csv_codes

    def test_subclass_match(self) -> None:
        """Every subclass in Python table matches the CSV."""
        with _CSV_PATH.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            csv_subclasses = [row[2] for row in reader]
        python_subclasses = [row[1] for row in _CLASSIFICATION_TABLE]
        assert python_subclasses == csv_subclasses
