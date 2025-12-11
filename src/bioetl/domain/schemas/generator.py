"""Helpers for generating Pandera schemas from column descriptors.

This module provides utilities for dynamically creating Pandera schemas,
particularly useful for cases where schema structure is determined at
runtime.
"""

from __future__ import annotations

import importlib

__all__ = ["generate_schema_from_column_order", "load_column_order_from_yaml"]


def generate_schema_from_column_order(columns: list[str]):
    """Build a permissive Pandera schema using the provided column order.

    Creates a schema where all columns are typed as `object` with nullable=True.
    This is useful for initial data loading before strict validation.

    Parameters
    ----------
    columns
        List of column names in desired order.

    Returns
    -------
    pa.DataFrameSchema
        A permissive schema accepting any data types.

    Examples
    --------
    >>> import pandas as pd
    >>> schema = generate_schema_from_column_order(["id", "name", "value"])
    >>> df = pd.DataFrame({"id": [1], "name": ["test"], "value": [1.5]})
    >>> validated = schema.validate(df)
    """
    pa = importlib.import_module("pandera.pandas")
    schema = pa.DataFrameSchema(
        {col: pa.Column(object, nullable=True, coerce=True) for col in columns}
    )
    return schema


def load_column_order_from_yaml(path: str | "Path") -> list[str]:
    import importlib
    from pathlib import Path as _P

    p = _P(path)
    yaml = importlib.import_module("yaml")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [str(x) for x in data]
    if isinstance(data, dict) and "columns" in data:
        cols = data["columns"]
        if isinstance(cols, list):
            return [str(x) for x in cols]
    raise ValueError("Invalid column-order YAML format")
