"""Custom Pandera checks for schema validation.

Provides reusable validation checks for JSON fields stored as strings.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pandas as pd
import pandera as pa

if TYPE_CHECKING:
    pass

__all__ = [
    "is_valid_json",
    "is_valid_json_array",
    "is_valid_json_object",
    "json_array_check",
    "json_check",
    "json_object_check",
]


def is_valid_json(series: pd.Series) -> pd.Series:
    """Check that non-null values are valid JSON.

    Args:
        series: Pandas Series to validate.

    Returns:
        Boolean Series indicating validity.
    """

    def check(val: object) -> bool:
        if pd.isna(val):
            return True
        try:
            json.loads(str(val))
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    return series.apply(check)


def is_valid_json_array(series: pd.Series) -> pd.Series:
    """Check that non-null values are valid JSON arrays.

    Args:
        series: Pandas Series to validate.

    Returns:
        Boolean Series indicating validity.
    """

    def check(val: object) -> bool:
        if pd.isna(val):
            return True
        try:
            parsed = json.loads(str(val))
            return isinstance(parsed, list)
        except (json.JSONDecodeError, TypeError):
            return False

    return series.apply(check)


def is_valid_json_object(series: pd.Series) -> pd.Series:
    """Check that non-null values are valid JSON objects.

    Args:
        series: Pandas Series to validate.

    Returns:
        Boolean Series indicating validity.
    """

    def check(val: object) -> bool:
        if pd.isna(val):
            return True
        try:
            parsed = json.loads(str(val))
            return isinstance(parsed, dict)
        except (json.JSONDecodeError, TypeError):
            return False

    return series.apply(check)


# Pre-built checks for use in schema definitions
json_check = pa.Check(is_valid_json, name="valid_json")
json_array_check = pa.Check(is_valid_json_array, name="valid_json_array")
json_object_check = pa.Check(is_valid_json_object, name="valid_json_object")
