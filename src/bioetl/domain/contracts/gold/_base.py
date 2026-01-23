"""Base utilities for Gold layer data contracts.

Contains shared constants and utilities used across all Gold schemas.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Regex pattern for date validation (YYYY-MM-DD format)
# Used for fields like publication_date, accepted_date, etc.
DATE_REGEX = r"^\d{4}-\d{2}-\d{2}$"
_DATE_PATTERN = re.compile(DATE_REGEX)


def validate_date_format(series: pd.Series[Any]) -> pd.Series[bool]:
    """Validate date format YYYY-MM-DD for a pandas Series.

    Workaround for Pandera 0.26.1 + Python 3.14 compatibility issue
    where str_matches field parameter fails with KeyError for pandas.Series
    due to function dispatch not recognizing pandas.Series type.

    Args:
        series: pandas Series to validate.

    Returns:
        Boolean Series where True indicates valid date format.
    """
    # Handle NaN values - they are valid (nullable field)
    return series.isna() | series.astype(str).str.match(_DATE_PATTERN)


__all__ = ["DATE_REGEX", "validate_date_format"]
