"""Base utilities for Gold layer data contracts.

Contains shared constants and utilities used across all Gold schemas.
"""

from __future__ import annotations

# Regex pattern for date validation (YYYY-MM-DD format)
# Used for fields like publication_date, accepted_date, etc.
DATE_REGEX = r"^\d{4}-\d{2}-\d{2}$"

__all__ = ["DATE_REGEX"]
