"""Shared mixins and helpers for ChEMBL Pandera schemas.

.. deprecated::
    This module is deprecated. Import from:
    - ``bioetl.infrastructure.validation.schemas.pandera_base``

Terminology:
    acquisition_timestamp: Timestamp when the data was acquired from the source.
        Deprecated alias: extracted_at (will be removed in v3.0).
"""

import warnings

# Re-export from infrastructure for backward compatibility
from bioetl.infrastructure.validation.schemas.pandera_base import (
    HEX_64_PATTERN,
    GENERATED_COLUMN_ORDER,
    DEPRECATED_COLUMN_ALIASES,
    build_output_column_order,
    BaseGeneratedColumnsModel,
    BaseGeneratedColumnsSchema,
)

__all__ = [
    "HEX_64_PATTERN",
    "GENERATED_COLUMN_ORDER",
    "DEPRECATED_COLUMN_ALIASES",
    "build_output_column_order",
    "BaseGeneratedColumnsModel",
    "BaseGeneratedColumnsSchema",
]

# Note: Deprecation warnings are emitted via __getattr__ in parent __init__.py
# to avoid noise during normal usage while still informing developers.
