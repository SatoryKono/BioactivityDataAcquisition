"""Base utilities for Gold layer data contracts.

Contains shared constants and utilities used across all Gold schemas.

Note on str_matches validation:
    The DATE_REGEX was previously used with pa.Field(str_matches=DATE_REGEX) for date
    validation. However, Pandera 0.26.1 has a compatibility issue with Python 3.14 where
    the str_matches parameter fails with KeyError for pandas.Series due to function
    dispatch not recognizing the type. Date format validation is now delegated to
    transformers which ensure correct YYYY-MM-DD format during data processing.
"""

from __future__ import annotations

# Regex pattern for date validation (YYYY-MM-DD format)
# Retained for documentation and potential future use when Pandera fixes the issue.
DATE_REGEX = r"^\d{4}-\d{2}-\d{2}$"

__all__ = ["DATE_REGEX"]
