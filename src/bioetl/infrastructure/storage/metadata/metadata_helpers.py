"""Metadata helpers for storage-side metadata adaptation and validation."""

from __future__ import annotations

import inspect
from typing import Any, Literal, cast

from pandera.errors import SchemaDefinitionError, SchemaInitError

from bioetl.domain.models.metadata import (
    SchemaColumnInspection,
    SchemaInspectionResult,
)

__all__ = [
    "build_and_validate_metadata",
    "inspect_schema_metadata",
]

_BIOETL_MODULE_PREFIX = "bioetl."
_SCHEMA_CONSTRUCTION_ERRORS = (
    AttributeError,
    TypeError,
    ValueError,
    SchemaDefinitionError,
    SchemaInitError,
)


def _build_metadata(key: str, value: str) -> dict[str, str]:
    """Build the raw metadata payload before validation.

    Uses the caller-supplied ``key`` as the payload key (not a literal
    ``\"key\"``), so ``build_and_validate_metadata(\"run_id\", \"abc\")`` yields
    ``{\"run_id\": \"abc\"}``.
    """
    return {key: value}


def build_and_validate_metadata(key: str, value: str) -> dict[str, str]:
    """Build and validate metadata dictionary.

    Args:
        key: Metadata key.
        value: Metadata value.

    Returns:
        Validated metadata dictionary.

    Raises:
        ValueError: If metadata is empty.
    """
    metadata = _build_metadata(key, value)
    if not metadata:
        raise ValueError("Metadata is empty")
    return metadata


def inspect_schema_metadata(
    gold_schema: object | None,
) -> SchemaInspectionResult | None:
    """Inspect a Pandera schema behind the infrastructure boundary.

    Known schema-construction failures remain fail-soft. Unexpected exceptions
    propagate so metadata generation cannot hide unrelated defects.
    """
    if gold_schema is None:
        return None

    return SchemaInspectionResult(
        contract_path=_extract_contract_path(gold_schema),
        version=_extract_schema_version(gold_schema),
        validation=_extract_validation_mode(gold_schema),
        columns=_extract_schema_columns(gold_schema),
    )


def _extract_contract_path(gold_schema: object) -> str | None:
    """Derive a stable source-style contract path from the import path."""
    try:
        module = inspect.getmodule(gold_schema)
        module_name = getattr(module, "__name__", "")
    except (AttributeError, OSError, TypeError):
        return None
    if not module_name.startswith(_BIOETL_MODULE_PREFIX):
        return None
    return f"src/{module_name.replace('.', '/')}.py"


def _get_config(gold_schema: object) -> object | None:
    """Return a schema Config surface when present."""
    host = cast(Any, gold_schema)  # Any: duck-typed Pandera schema class
    return host.Config if hasattr(gold_schema, "Config") else None


def _extract_schema_version(gold_schema: object) -> str:
    """Extract and normalize the schema version."""
    config = _get_config(gold_schema)
    version = getattr(config, "version", "1.0")
    return version if isinstance(version, str) else str(version)


def _extract_validation_mode(
    gold_schema: object,
) -> Literal["strict", "lenient"]:
    """Extract the strict/lenient validation mode."""
    config = _get_config(gold_schema)
    return "strict" if getattr(config, "strict", True) else "lenient"


def _extract_schema_columns(
    gold_schema: object,
) -> tuple[SchemaColumnInspection, ...]:
    """Inspect schema columns while containing known Pandera failures."""
    try:
        schema_instance = _safe_to_schema(gold_schema)
    except _SCHEMA_CONSTRUCTION_ERRORS:
        return ()

    raw_columns = getattr(schema_instance, "columns", None)
    if not isinstance(raw_columns, dict):
        return ()
    return tuple(
        _inspect_schema_column(str(name), column)
        for name, column in raw_columns.items()
    )


def _safe_to_schema(gold_schema: object) -> object:
    """Build a Pandera schema instance when the class exposes ``to_schema``."""
    to_schema = getattr(gold_schema, "to_schema", None)
    if callable(to_schema):
        return to_schema()
    return gold_schema


def _inspect_schema_column(
    name: str,
    column: object,
) -> SchemaColumnInspection:
    """Convert one Pandera column into primitive inspection data."""
    raw_dtype = getattr(column, "dtype", None)
    return SchemaColumnInspection(
        name=name,
        dtype=str(raw_dtype) if raw_dtype is not None else "object",
        nullable=bool(getattr(column, "nullable", True)),
    )
