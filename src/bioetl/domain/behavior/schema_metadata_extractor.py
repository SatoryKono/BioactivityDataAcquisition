# Host attrs/methods provided by concrete composition.
"""Shared schema metadata extraction for Gold metadata sidecars.

Provides one canonical implementation used by both composition and
infrastructure metadata builders.
"""

from __future__ import annotations

import inspect
from typing import Literal, cast, Any

from bioetl.domain.models.metadata import SchemaColumnMetadata, SchemaMetadata

__all__ = [
    "extract_schema_metadata",
]


def extract_schema_metadata(
    gold_schema: object | None,
) -> SchemaMetadata:
    """Extract schema metadata from a Pandera DataFrameModel class.

    Args:
        gold_schema: Pandera DataFrameModel class (not instance), or None.

    Returns:
        Populated SchemaMetadata. Returns default metadata when schema is None.
    """
    if gold_schema is None:
        return SchemaMetadata()

    contract_path = _extract_contract_path(gold_schema)
    version = _extract_schema_version(gold_schema)
    validation = _extract_validation_mode(gold_schema)
    columns = _extract_schema_columns(gold_schema)

    return SchemaMetadata(
        contract_path=contract_path,
        version=version,
        validation=validation,
        columns=columns,
    )


def _extract_contract_path(
    gold_schema: object,
) -> str | None:
    """Extract source path relative to project root from schema module."""
    try:
        module = inspect.getmodule(gold_schema)
        if module and module.__file__:
            file_path = module.__file__
            if "src/bioetl" in file_path:
                idx = file_path.find("src/bioetl")
                return file_path[idx:]
    except (AttributeError, OSError, TypeError):
        return None
    return None


def _extract_schema_version(
    gold_schema: object,
) -> str:
    """Extract schema version from inner Config class."""
    version = "1.0"
    host = cast(Any, gold_schema)  # Any: duck-type Config nested on schema class
    if hasattr(gold_schema, "Config"):
        config = host.Config
        version = getattr(config, "version", "1.0")
        if not isinstance(version, str):
            version = str(version)
    return version


def _extract_validation_mode(
    gold_schema: object,
) -> Literal["strict", "lenient"]:
    """Extract strict/lenient validation mode from inner Config class."""
    validation: Literal["strict", "lenient"] = "strict"
    host = cast(Any, gold_schema)  # Any: duck-type Config nested on schema class
    if hasattr(gold_schema, "Config"):
        config = host.Config
        is_strict = getattr(config, "strict", True)
        validation = "strict" if is_strict else "lenient"
    return validation


def _extract_schema_columns(
    gold_schema: object,
) -> list[SchemaColumnMetadata]:
    """Extract columns from schema via to_schema() when available."""
    try:
        schema_instance = _safe_to_schema(gold_schema)
    except (AttributeError, TypeError, ValueError):
        return []

    raw_columns = getattr(schema_instance, "columns", None)
    if not isinstance(raw_columns, dict):
        return []

    return [
        _build_schema_column_metadata(col_name, col_schema)
        for col_name, col_schema in raw_columns.items()
    ]


def _safe_to_schema(gold_schema: object) -> object:
    """Return schema object via to_schema when available."""
    to_schema = getattr(gold_schema, "to_schema", None)
    if callable(to_schema):
        return to_schema()
    return object()


def _build_schema_column_metadata(
    col_name: str,
    col_schema: object,
) -> SchemaColumnMetadata:
    """Build normalized metadata DTO for one schema column."""
    raw_dtype = getattr(col_schema, "dtype", None)
    dtype_str = str(raw_dtype) if raw_dtype is not None else "object"
    if "." in dtype_str:
        dtype_str = dtype_str.split(".")[-1]
    return SchemaColumnMetadata(
        name=col_name,
        type=dtype_str,
        nullable=getattr(col_schema, "nullable", True),
    )
