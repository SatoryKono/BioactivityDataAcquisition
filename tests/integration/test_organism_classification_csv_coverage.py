"""Integration coverage for organism classification against current input data."""

from __future__ import annotations

import csv
from pathlib import Path

from bioetl.domain.mapping.organism_classification import classify_organism


def test_all_distinct_organisms_in_current_target_csv_resolve() -> None:
    """Current ChEMBL target CSV should remain classifiable by organism name."""
    path = Path("data/input/target.csv")
    rows = csv.DictReader(path.open(newline="", encoding="utf-8"))

    unresolved: list[str] = []
    for organism_name in sorted(
        {(row.get("organism") or "").strip() for row in rows if row.get("organism")}
    ):
        result = classify_organism(organism_name, None)
        if result.organism_class is None:
            unresolved.append(organism_name)

    assert unresolved == []
