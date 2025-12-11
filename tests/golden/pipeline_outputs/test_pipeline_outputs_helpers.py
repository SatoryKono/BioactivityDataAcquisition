"""Utilities for loading golden pipeline outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd
import pytest

_UNSTABLE_COLUMNS: set[str] = {
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
}


class MissingDataFile:
    """Sentinel class to indicate missing data file for pytest skip."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __repr__(self) -> str:
        return f"MissingDataFile({self.path})"


def load_expected_records(
    csv_path: Path, *, sort_key: str
) -> Union[list[dict[str, object]], MissingDataFile]:
    """Load expected records from a CSV snapshot dropping unstable columns.

    Returns MissingDataFile sentinel if the file does not exist.
    """
    if not csv_path.exists():
        return MissingDataFile(csv_path)

    df = pd.read_csv(csv_path)
    df = df.drop(columns=[col for col in _UNSTABLE_COLUMNS if col in df.columns])
    df = df.sort_values(by=sort_key).head(5)

    return [
        {key: (None if pd.isna(value) else value) for key, value in record.items()}
        for record in df.to_dict(orient="records")
    ]


def skip_if_missing(
    data: Union[list[dict[str, object]], MissingDataFile],
) -> list[dict[str, object]]:
    """Skip test if data is MissingDataFile sentinel."""
    if isinstance(data, MissingDataFile):
        pytest.skip(f"Data file not found: {data.path}")
    return data


__all__ = ["load_expected_records", "MissingDataFile", "skip_if_missing"]
