"""Utilities for loading golden pipeline outputs."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

_UNSTABLE_COLUMNS: set[str] = {
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
}


def load_expected_records(csv_path: Path, *, sort_key: str) -> list[dict[str, object]]:
    """Load expected records from a CSV snapshot dropping unstable columns."""

    df = pd.read_csv(csv_path)
    df = df.drop(columns=[col for col in _UNSTABLE_COLUMNS if col in df.columns])
    df = df.sort_values(by=sort_key).head(5)

    return [
        {key: (None if pd.isna(value) else value) for key, value in record.items()}
        for record in df.to_dict(orient="records")
    ]


__all__ = ["load_expected_records"]
