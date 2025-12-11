"""Infrastructure schema bootstrap module.

This module provides the implementation for registering concrete Pandera schemas
with the schema registry. It resides in the infrastructure layer because it
depends on the concrete schema implementations.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from bioetl.domain.validation import SchemaProviderABC
from bioetl.infrastructure.validation.schemas.chembl import (
    ACTIVITY_OUTPUT_COLUMNS,
    ASSAY_OUTPUT_COLUMNS,
    CELL_OUTPUT_COLUMNS,
    MOLECULE_OUTPUT_COLUMNS,
    PUBLICATION_OUTPUT_COLUMNS,
    TARGET_OUTPUT_COLUMNS,
    TISSUE_OUTPUT_COLUMNS,
    ActivityTableSchema,
    AssayTableSchema,
    CellTableSchema,
    MoleculeTableSchema,
    PublicationTableSchema,
    TargetTableSchema,
    TissueTableSchema,
)

__all__ = ["register_schemas"]

_SchemaDef = tuple[type[Any], Sequence[str] | None]

_SCHEMA_DEFINITIONS: dict[str, _SchemaDef] = {
    "activity": (ActivityTableSchema, ACTIVITY_OUTPUT_COLUMNS),
    "assay": (AssayTableSchema, ASSAY_OUTPUT_COLUMNS),
    "cell": (CellTableSchema, CELL_OUTPUT_COLUMNS),
    "molecule": (MoleculeTableSchema, MOLECULE_OUTPUT_COLUMNS),
    "publication": (PublicationTableSchema, PUBLICATION_OUTPUT_COLUMNS),
    "target": (TargetTableSchema, TARGET_OUTPUT_COLUMNS),
    "tissue": (TissueTableSchema, TISSUE_OUTPUT_COLUMNS),
}

_SCHEMA_ALIASES: dict[str, str] = {
    "document": "publication",
}


def _resolve_column_order(
    schema_cls: type[Any],
    declared_order: Sequence[str] | None,
) -> list[str]:
    """Return column order for schema, preserving declared ordering when available."""
    if declared_order is not None:
        return list(declared_order)

    schema = schema_cls.to_schema()
    columns = getattr(schema, "columns", None)
    if columns is None or not hasattr(columns, "keys"):
        raise ValueError(
            f"Schema '{schema_cls.__name__}' does not expose ordered columns."
        )
    return list(columns.keys())


def _iter_variants(base_name: str) -> tuple[str, str, str]:
    """Return canonical schema name aliases for pipeline stages."""
    return base_name, f"{base_name}_input", f"{base_name}_output"


def _register_with_variants(
    schema_provider: SchemaProviderABC,
    schema_name: str,
    schema_cls: type[Any],
    column_order: list[str],
) -> None:
    for variant in _iter_variants(schema_name):
        schema_provider.register(
            variant,
            schema_cls,
            column_order=list(column_order),
        )


def register_schemas(schema_provider: SchemaProviderABC) -> SchemaProviderABC:
    """
    Register all supported Pandera schemas in the provided registry.

    Ensures each entity name exposes schema, *_input, and *_output aliases.
    """

    for entity_name in sorted(_SCHEMA_DEFINITIONS):
        schema_cls, declared_order = _SCHEMA_DEFINITIONS[entity_name]
        column_order = _resolve_column_order(schema_cls, declared_order)
        _register_with_variants(schema_provider, entity_name, schema_cls, column_order)

    for alias, target in sorted(_SCHEMA_ALIASES.items()):
        if target not in _SCHEMA_DEFINITIONS:
            msg = f"Schema alias '{alias}' references unknown target '{target}'."
            raise ValueError(msg)
        schema_cls, declared_order = _SCHEMA_DEFINITIONS[target]
        column_order = _resolve_column_order(schema_cls, declared_order)
        _register_with_variants(schema_provider, alias, schema_cls, column_order)

    return schema_provider
