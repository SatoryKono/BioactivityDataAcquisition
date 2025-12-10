"""Base Pandera schema with generated columns support.

This module provides the foundation for all Pandera DataFrameModel schemas
in the validation infrastructure. It defines:

- Generated (service) columns that are common to all schemas
- Base configuration for strict validation, coercion, and ordering
- Helper functions for building output column orders
"""

from __future__ import annotations

from typing import Any

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.field_specs import GENERATED_COLUMN_NAMES

__all__ = [
    "HEX_64_PATTERN",
    "GENERATED_COLUMN_ORDER",
    "DEPRECATED_COLUMN_ALIASES",
    "build_output_column_order",
    "BaseGeneratedColumnsModel",
    "BaseGeneratedColumnsSchema",
]

# Regex pattern for SHA-256 hash validation
HEX_64_PATTERN = r"^[a-f0-9]{64}$"

# Canonical column names for generated columns (derived from domain specs)
GENERATED_COLUMN_ORDER: list[str] = list(GENERATED_COLUMN_NAMES)

# Deprecated column name mapping (for backward compatibility)
# TODO: Remove in v3.0
DEPRECATED_COLUMN_ALIASES: dict[str, str] = {
    "extracted_at": "acquisition_timestamp",
}


def build_output_column_order(business_columns: list[str]) -> list[str]:
    """Append generated columns to business column order.

    Parameters
    ----------
    business_columns
        List of business (domain-specific) column names.

    Returns
    -------
    list[str]
        Business columns followed by generated columns.
    """
    return [*business_columns, *GENERATED_COLUMN_ORDER]


# Type aliases for internal use
_FieldDefinition = tuple[Any, Any]
_FieldMapping = dict[str, _FieldDefinition]


class BaseGeneratedColumnsModel(pa.DataFrameModel):
    """Base schema with common generated/service columns.

    All entity schemas should inherit from this class to include
    the standard generated columns (hash_row, hash_business_key,
    index, database_version, acquisition_timestamp).

    Column naming:
        acquisition_timestamp: Canonical name for data acquisition timestamp.
            Deprecated alias: extracted_at (will be removed in v3.0).

    Configuration:
        strict = True: Fail on extra columns not in schema
        coerce = True: Attempt type coercion before validation
        ordered = True: Validate column order
    """

    hash_row: Series[str] = pa.Field(
        str_matches=HEX_64_PATTERN,
        description="SHA-256 hash of entire row (64 hex characters)",
    )
    hash_business_key: Series[str] = pa.Field(
        nullable=True,
        str_matches=HEX_64_PATTERN,
        description="SHA-256 hash of business key",
    )
    index: Series[int] = pa.Field(ge=0, description="Row order number")
    database_version: Series[str] = pa.Field(
        nullable=True, description="Source database version"
    )
    acquisition_timestamp: Series[str] = pa.Field(
        nullable=True,
        description="Timestamp when data was acquired from source",
    )

    class Config:
        """Strict Pandera configuration for all schemas."""

        strict = True
        coerce = True
        ordered = True

    @classmethod
    def _collect_fields(cls) -> _FieldMapping:
        """Reorder fields to place generated columns at the end.

        This ensures that regardless of declaration order in subclasses,
        the generated columns always appear at the end of the schema.
        """
        fields = super()._collect_fields()
        if cls is BaseGeneratedColumnsModel or not fields:
            return fields

        return cls._append_generated_columns(fields)

    @staticmethod
    def _append_generated_columns(fields: _FieldMapping) -> _FieldMapping:
        """Return a copy of field mapping with generated columns at the end.

        Parameters
        ----------
        fields
            Original field mapping from Pandera.

        Returns
        -------
        _FieldMapping
            Reordered field mapping with generated columns last.
        """
        generated = {
            name: fields[name] for name in GENERATED_COLUMN_ORDER if name in fields
        }
        ordered_fields: _FieldMapping = {}

        # Add non-generated fields first
        for name, value in fields.items():
            if name in generated:
                continue
            ordered_fields[name] = value

        # Add generated fields at the end in canonical order
        for name in GENERATED_COLUMN_ORDER:
            definition = generated.get(name)
            if definition is None:
                continue
            ordered_fields[name] = definition

        return ordered_fields


# Backward compatibility alias for existing imports
BaseGeneratedColumnsSchema = BaseGeneratedColumnsModel
