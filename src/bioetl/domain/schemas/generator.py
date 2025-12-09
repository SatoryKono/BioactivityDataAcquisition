"""Helpers for generating Pandera schemas from column descriptors."""

from __future__ import annotations

from pathlib import Path

import pandera as pa
import yaml

__all__ = [
    "generate_schema_from_column_order",
    "load_column_order_from_yaml",
]


def generate_schema_from_column_order(columns: list[str]) -> pa.DataFrameSchema:
    """Build a permissive Pandera schema using the provided column order."""

    return pa.DataFrameSchema(
        {col: pa.Column(object, nullable=True, coerce=True) for col in columns}
    )


def load_column_order_from_yaml(path: str | Path) -> list[str]:
    """Load ordered column names from a YAML file."""

    raw = Path(path).read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)

    if not isinstance(loaded, list) or not all(isinstance(item, str) for item in loaded):
        msg = "columns.yaml must contain a list of strings"
        raise ValueError(msg)

    return list(loaded)
