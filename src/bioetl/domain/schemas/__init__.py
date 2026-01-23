"""Domain schemas for ETL records.

Provides:
- Base Pandera schemas for validation
- Canonical column ordering utilities
- Provider-specific schema definitions
"""

from __future__ import annotations

from bioetl.domain.schemas.column_order import (
    ALL_SYSTEM_FIELDS,
    DQ_FIELDS_SUFFIX,
    SYSTEM_FIELDS_PREFIX,
    LOOKUP_FIELDS_PREFIX,
    canonical_column_order,
)

__all__ = [
    "ALL_SYSTEM_FIELDS",
    "DQ_FIELDS_SUFFIX",
    "LOOKUP_FIELDS_PREFIX",
    "SYSTEM_FIELDS_PREFIX",
    "canonical_column_order",
]
