"""Shared schema metadata extraction for Gold metadata sidecars.

Provides one canonical implementation used by both composition and
infrastructure metadata builders.
"""

from __future__ import annotations

import inspect
from typing import Any, Literal

from bioetl.domain.models.metadata import SchemaColumnMetadata, SchemaMetadata


def extract_schema_metadata(gold_schema: Any | None) -> SchemaMetadata:
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


def _extract_contract_path(gold_schema: Any) -> str | None:
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


def _extract_schema_version(gold_schema: Any) -> str:
    """Extract schema version from inner Config class."""
    version = "1.0"
    if hasattr(gold_schema, "Config"):
        config = gold_schema.Config
        version = getattr(config, "version", "1.0")
        if not isinstance(version, str):
            version = str(version)
    return version


def _extract_validation_mode(gold_schema: Any) -> Literal["strict", "lenient"]:
    """Extract strict/lenient validation mode from inner Config class."""
    validation: Literal["strict", "lenient"] = "strict"
    if hasattr(gold_schema, "Config"):
        config = gold_schema.Config
        is_strict = getattr(config, "strict", True)
        validation = "strict" if is_strict else "lenient"
    return validation


def _extract_schema_columns(gold_schema: Any) -> list[SchemaColumnMetadata]:
    """Extract columns from schema via to_schema() when available."""
    columns: list[SchemaColumnMetadata] = []
    try:
        if hasattr(gold_schema, "to_schema"):
            schema_instance = gold_schema.to_schema()
            if hasattr(schema_instance, "columns"):
                for col_name, col_schema in schema_instance.columns.items():
                    dtype_str = str(col_schema.dtype) if col_schema.dtype else "object"
                    if "." in dtype_str:
                        dtype_str = dtype_str.split(".")[-1]

                    nullable = getattr(col_schema, "nullable", True)
                    columns.append(
                        SchemaColumnMetadata(
                            name=col_name,
                            type=dtype_str,
                            nullable=nullable,
                        )
                    )
    except (AttributeError, TypeError, ValueError):
        columns = []
    return columns
