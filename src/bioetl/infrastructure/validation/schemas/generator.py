"""Helpers for generating Pandera schemas from column descriptors.

This module provides utilities for dynamically creating Pandera schemas,
particularly useful for cases where schema structure is determined at
runtime or loaded from external configuration.
"""

from __future__ import annotations

from pathlib import Path

import pandera.pandas as pa
import yaml

__all__ = [
    "generate_schema_from_column_order",
    "load_column_order_from_yaml",
]


def generate_schema_from_column_order(columns: list[str]) -> pa.DataFrameSchema:
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
    >>> schema = generate_schema_from_column_order(["id", "name", "value"])
    >>> df = pd.DataFrame({"id": [1], "name": ["test"], "value": [1.5]})
    >>> validated = schema.validate(df)
    """
    schema = pa.DataFrameSchema(
        {col: pa.Column(object, nullable=True, coerce=True) for col in columns}
    )
    return schema


def load_column_order_from_yaml(path: str | Path) -> list[str]:
    """Load ordered column names from a YAML file.

    Parameters
    ----------
    path
        Path to YAML file containing a list of column names.

    Returns
    -------
    list[str]
        Ordered list of column names.

    Raises
    ------
    ValueError
        If the YAML content is not a list of strings.
    FileNotFoundError
        If the file does not exist.

    Examples
    --------
    Given a file `columns.yaml`:
    ```yaml
    - id
    - name
    - value
    ```

    >>> columns = load_column_order_from_yaml("columns.yaml")
    >>> columns
    ['id', 'name', 'value']
    """
    raw = Path(path).read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)

    if not isinstance(loaded, list) or not all(
        isinstance(item, str) for item in loaded
    ):
        msg = "YAML file must contain a list of strings"
        raise ValueError(msg)

    return list(loaded)
