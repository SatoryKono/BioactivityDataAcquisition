"""Pandera schema implementations for data validation.

This module provides Pandera-based schema implementations that
validate data against domain field specifications.

Architecture:
    domain/schemas/field_specs.py  -> Technology-agnostic field definitions
    infrastructure/validation/schemas/ -> Pandera schema implementations

The schemas here use domain field specifications as the source of truth
for field definitions, while Pandera provides the validation mechanics.
"""

from bioetl.infrastructure.validation.schemas.pandera_base import (
    BaseGeneratedColumnsModel,
    BaseGeneratedColumnsSchema,
    GENERATED_COLUMN_ORDER,
    HEX_64_PATTERN,
    build_output_column_order,
)
from bioetl.infrastructure.validation.schemas.adapter import (
    field_spec_to_pandera_field,
    field_specs_to_schema_fields,
)

__all__ = [
    # Base schema classes
    "BaseGeneratedColumnsModel",
    "BaseGeneratedColumnsSchema",
    # Helpers
    "GENERATED_COLUMN_ORDER",
    "HEX_64_PATTERN",
    "build_output_column_order",
    # Adapter functions
    "field_spec_to_pandera_field",
    "field_specs_to_schema_fields",
]
