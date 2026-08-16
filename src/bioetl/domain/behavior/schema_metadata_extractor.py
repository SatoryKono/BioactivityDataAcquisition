"""Shared schema metadata extraction for Gold metadata sidecars.

Normalizes framework-neutral schema inspection results into Domain metadata.
"""

from __future__ import annotations

from bioetl.domain.models.metadata import (
    SchemaColumnInspection,
    SchemaColumnMetadata,
    SchemaInspectionResult,
    SchemaMetadata,
)

__all__ = [
    "extract_schema_metadata",
]


def extract_schema_metadata(
    inspection: SchemaInspectionResult | None,
) -> SchemaMetadata:
    """Normalize a framework-neutral schema inspection result.

    Args:
        inspection: Adapter-produced inspection data, or ``None``.

    Returns:
        Populated metadata, or defaults when no schema was inspected.
    """
    if inspection is None:
        return SchemaMetadata()

    return SchemaMetadata(
        contract_path=inspection.contract_path,
        version=inspection.version,
        validation=inspection.validation,
        columns=[_normalize_column(column) for column in inspection.columns],
    )


def _normalize_column(
    column: SchemaColumnInspection,
) -> SchemaColumnMetadata:
    """Normalize one adapter-produced schema column."""
    dtype_str = column.dtype or "object"
    if "." in dtype_str:
        dtype_str = dtype_str.split(".")[-1]
    return SchemaColumnMetadata(
        name=column.name,
        type=dtype_str,
        nullable=column.nullable,
    )
