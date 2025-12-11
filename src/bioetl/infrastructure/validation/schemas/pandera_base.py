"""Base Pandera schema with generated columns support.

This module provides the foundation for all Pandera DataFrameModel schemas
in the validation infrastructure. It defines:

- Generated (service) columns that are common to all schemas
- Base configuration for strict validation, coercion, and ordering
- Helper functions for building output column orders
- Deprecation handling for legacy column names (extracted_at -> acquisition_timestamp)
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.field_specs import GENERATED_COLUMN_NAMES, HEX_64_PATTERN

if TYPE_CHECKING:
    import pandas as pd

__all__ = [
    "HEX_64_PATTERN",
    "GENERATED_COLUMN_ORDER",
    "DEPRECATED_COLUMN_ALIASES",
    "build_output_column_order",
    "migrate_deprecated_columns",
    "check_deprecated_columns",
    "BaseGeneratedColumnsModel",
    "BaseGeneratedColumnsSchema",
]

# Regex pattern for SHA-256 hash validation
# Imported from domain.schemas.field_specs

# Canonical column names for generated columns (derived from domain specs)
GENERATED_COLUMN_ORDER: list[str] = list(GENERATED_COLUMN_NAMES)

# Deprecated column name mapping (for backward compatibility)
# TODO: Remove in v3.0
DEPRECATED_COLUMN_ALIASES: dict[str, str] = {
    "extracted_at": "acquisition_timestamp",
}


def check_deprecated_columns(
    columns: list[str],
    *,
    warn: bool = True,
    stacklevel: int = 3,
) -> list[str]:
    """Check for deprecated column names and optionally warn.

    Args:
        columns: List of column names to check.
        warn: Whether to emit deprecation warnings.
        stacklevel: Stack level for warnings.

    Returns:
        List of deprecated column names found.

    Example:
        >>> deprecated = check_deprecated_columns(df.columns.tolist())
        >>> if deprecated:
        ...     print(f"Found deprecated columns: {deprecated}")
    """
    found_deprecated: list[str] = []

    for col in columns:
        if col in DEPRECATED_COLUMN_ALIASES:
            found_deprecated.append(col)

    if warn and found_deprecated:
        canonical_names = [DEPRECATED_COLUMN_ALIASES[c] for c in found_deprecated]
        warnings.warn(
            f"Deprecated column names detected: {found_deprecated}. "
            f"Please rename to canonical names: {canonical_names}. "
            "Deprecated column names will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=stacklevel,
        )

    return found_deprecated


def migrate_deprecated_columns(
    df: pd.DataFrame,
    *,
    inplace: bool = False,
    warn: bool = True,
) -> pd.DataFrame:
    """Migrate deprecated column names to canonical names.

    This function renames columns from deprecated names to their
    canonical equivalents (e.g., 'extracted_at' -> 'acquisition_timestamp').

    Args:
        df: DataFrame to migrate.
        inplace: Whether to modify the DataFrame in place.
        warn: Whether to emit deprecation warnings.

    Returns:
        DataFrame with renamed columns (same object if inplace=True).

    Example:
        >>> df = migrate_deprecated_columns(df)
        >>> assert "acquisition_timestamp" in df.columns
        >>> assert "extracted_at" not in df.columns
    """
    columns_to_rename: dict[str, str] = {}

    for old_name, new_name in DEPRECATED_COLUMN_ALIASES.items():
        if old_name in df.columns and new_name not in df.columns:
            columns_to_rename[old_name] = new_name

    if not columns_to_rename:
        return df

    if warn:
        old_names = list(columns_to_rename.keys())
        new_names = list(columns_to_rename.values())
        warnings.warn(
            f"Migrating deprecated columns {old_names} -> {new_names}. "
            "Please update your data pipelines to use canonical column names. "
            "Automatic migration will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=3,
        )

    return df.rename(columns=columns_to_rename, inplace=inplace) or df


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

    # Canonical term: record_hash (contract method: compute_fingerprint)
    hash_row: Series[str] = pa.Field(
        str_matches=HEX_64_PATTERN,
        description="SHA-256 hash of entire row (canonical: record_hash)",
    )
    # Canonical term: business_key_hash (contract method: compute_entity_key)
    hash_business_key: Series[str] = pa.Field(
        nullable=True,
        str_matches=HEX_64_PATTERN,
        description="SHA-256 hash of business key (canonical: business_key_hash)",
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
