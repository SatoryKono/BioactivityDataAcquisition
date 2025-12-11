"""Output column descriptors for ChEMBL schemas."""

from __future__ import annotations

from bioetl.domain.schemas.field_specs import (
    ACTIVITY_FIELD_SPECS,
    ASSAY_FIELD_SPECS,
    CELL_FIELD_SPECS,
    GENERATED_COLUMN_NAMES,
    MOLECULE_FIELD_SPECS,
    PUBLICATION_FIELD_SPECS,
    TARGET_FIELD_SPECS,
    TISSUE_FIELD_SPECS,
    FieldSpec,
)


def _build_column_order(specs: tuple[FieldSpec, ...]) -> list[str]:
    """Build column order from field specs + generated columns."""
    return [f.name for f in specs] + list(GENERATED_COLUMN_NAMES)


ACTIVITY_OUTPUT_COLUMNS: list[str] = _build_column_order(ACTIVITY_FIELD_SPECS)
ASSAY_OUTPUT_COLUMNS: list[str] = _build_column_order(ASSAY_FIELD_SPECS)
CELL_OUTPUT_COLUMNS: list[str] = _build_column_order(CELL_FIELD_SPECS)
MOLECULE_OUTPUT_COLUMNS: list[str] = _build_column_order(MOLECULE_FIELD_SPECS)
PUBLICATION_OUTPUT_COLUMNS: list[str] = _build_column_order(
    PUBLICATION_FIELD_SPECS
)
TARGET_OUTPUT_COLUMNS: list[str] = _build_column_order(TARGET_FIELD_SPECS)
TISSUE_OUTPUT_COLUMNS: list[str] = _build_column_order(TISSUE_FIELD_SPECS)

__all__ = [
    "ACTIVITY_OUTPUT_COLUMNS",
    "ASSAY_OUTPUT_COLUMNS",
    "CELL_OUTPUT_COLUMNS",
    "MOLECULE_OUTPUT_COLUMNS",
    "PUBLICATION_OUTPUT_COLUMNS",
    "TARGET_OUTPUT_COLUMNS",
    "TISSUE_OUTPUT_COLUMNS",
]
