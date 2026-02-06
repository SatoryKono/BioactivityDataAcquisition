"""Custom Pandera checks for schema validation.

Provides reusable validation checks for:
- JSON fields stored as strings
- Numeric range validations (registered via pandera.extensions)
- String format validations

Usage in DataFrameModel schemas:
    class MySchema(pa.DataFrameModel):
        mass: Series[float] = pa.Field(nullable=True, is_non_negative=True)
        score: Series[int] = pa.Field(nullable=True, in_range={"min_val": 0, "max_val": 100})
        smiles: Series[str] = pa.Field(nullable=True, max_str_length=10000)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pandas as pd
import pandera as pa
from pandera.extensions import register_check_method

if TYPE_CHECKING:
    pass

__all__ = [
    # JSON validators
    "is_valid_json",
    "is_valid_json_array",
    "is_valid_json_object",
    "json_array_check",
    "json_check",
    "json_object_check",
    # Registered check methods (use in pa.Field)
    "is_non_negative",
    "is_positive",
    "in_closed_range",
    "max_str_length",
    "str_starts_with",
    "str_matches_pattern",
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


# =============================================================================
# REGISTERED CHECK METHODS (for use in pa.Field)
# =============================================================================
# These are registered via pandera.extensions.register_check_method
# and can be used in pa.Field() as keyword arguments.


@register_check_method(
    statistics=["min_value"],
    supported_types=(pd.Series,),
)
def is_non_negative(
    pandas_obj: pd.Series, *, min_value: float | bool = 0
) -> pd.Series:
    """Check that values are non-negative (>= 0).

    Usage in schema:
        field: Series[float] = pa.Field(is_non_negative=True)

    Args:
        pandas_obj: Series to validate.
        min_value: When True (from is_non_negative=True), defaults to 0.
    """
    # When used as is_non_negative=True, min_value comes in as True
    actual_min = 0 if min_value is True else min_value
    return pandas_obj.isna() | (pandas_obj >= actual_min)


@register_check_method(
    statistics=["min_value"],
    supported_types=(pd.Series,),
)
def is_positive(pandas_obj: pd.Series, *, min_value: int | bool = 1) -> pd.Series:
    """Check that values are positive (>= 1).

    Usage in schema:
        field: Series[int] = pa.Field(is_positive=True)

    Args:
        pandas_obj: Series to validate.
        min_value: When True (from is_positive=True), defaults to 1.
    """
    # When used as is_positive=True, min_value comes in as True
    actual_min = 1 if min_value is True else min_value
    return pandas_obj.isna() | (pandas_obj >= actual_min)


@register_check_method(
    statistics=["min_val", "max_val"],
    supported_types=(pd.Series,),
)
def in_closed_range(
    pandas_obj: pd.Series,
    *,
    min_val: int | float,
    max_val: int | float,
) -> pd.Series:
    """Check that values are within inclusive range [min_val, max_val].

    Allows nulls. Use when pa.Field(ge=, le=) is not sufficient.

    Usage in schema:
        field: Series[int] = pa.Field(in_closed_range={"min_val": 0, "max_val": 100})
    """
    return pandas_obj.isna() | ((pandas_obj >= min_val) & (pandas_obj <= max_val))


@register_check_method(
    statistics=["max_len"],
    supported_types=(pd.Series,),
)
def max_str_length(pandas_obj: pd.Series, *, max_len: int) -> pd.Series:
    """Check that string length is within limit.

    Usage in schema:
        field: Series[str] = pa.Field(max_str_length={"max_len": 10000})
    """
    return pandas_obj.isna() | (pandas_obj.str.len() <= max_len)


@register_check_method(
    statistics=["prefix"],
    supported_types=(pd.Series,),
)
def str_starts_with(pandas_obj: pd.Series, *, prefix: str) -> pd.Series:
    """Check that strings start with a prefix.

    Usage in schema:
        field: Series[str] = pa.Field(str_starts_with={"prefix": "InChI="})
    """
    return pandas_obj.isna() | pandas_obj.str.startswith(prefix)


@register_check_method(
    statistics=["pattern"],
    supported_types=(pd.Series,),
)
def str_matches_pattern(pandas_obj: pd.Series, *, pattern: str) -> pd.Series:
    """Check that strings match a regex pattern.

    Usage in schema:
        field: Series[str] = pa.Field(str_matches_pattern={"pattern": r"^CHEMBL\\d+$"})
    """
    return pandas_obj.isna() | pandas_obj.str.match(pattern)
