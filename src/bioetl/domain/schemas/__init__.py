"""Domain schemas for ETL records.

Provides:
- Base Pandera schemas for validation
- Canonical column ordering utilities
- Provider-specific schema definitions
- JSON validators for schema checks
"""

from __future__ import annotations

from bioetl.domain.schemas.column_order import (
    ALL_SYSTEM_FIELDS,
    DQ_FIELDS_SUFFIX,
    LOOKUP_FIELDS_PREFIX,
    SYSTEM_FIELDS_PREFIX,
    canonical_column_order,
)
from bioetl.domain.schemas.validators import (
    json_array_check,
    json_check,
    json_object_check,
)

__all__ = [
    "ALL_SYSTEM_FIELDS",
    "DQ_FIELDS_SUFFIX",
    "LOOKUP_FIELDS_PREFIX",
    "SYSTEM_FIELDS_PREFIX",
    "canonical_column_order",
    "json_array_check",
    "json_check",
    "json_object_check",
]
