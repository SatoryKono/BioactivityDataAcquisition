"""Pandera schema definitions for ChEMBL cell dimension.

This schema validates the structure and content of cell line data
after normalization.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.field_specs import CHEMBL_ID_PATTERN
from bioetl.infrastructure.validation.schemas.pandera_base import (
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)

__all__ = ["CellTableSchema", "OUTPUT_COLUMN_ORDER"]

_CELL_BUSINESS_COLUMNS: list[str] = [
    "cell_chembl_id",
    "cell_name",
    "cell_source_organism",
    "cell_type",
    "cell_description",
]

OUTPUT_COLUMN_ORDER: list[str] = build_output_column_order(_CELL_BUSINESS_COLUMNS)


class CellTableSchema(BaseGeneratedColumnsSchema):
    """Normalized cell reference table exported from ChEMBL.

    Validates cell line definitions including:
    - ChEMBL identifier
    - Cell line metadata (name, type, organism)
    - Descriptions
    """

    cell_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_PATTERN,
        description="Primary ChEMBL cell identifier",
    )
    cell_name: Series[str] = pa.Field(
        nullable=True, description="Preferred cell line name"
    )
    cell_source_organism: Series[str] = pa.Field(
        nullable=True, description="Organism the cell line originates from"
    )
    cell_type: Series[str] = pa.Field(
        nullable=True, description="High-level cell type (epithelial, stem, etc.)"
    )
    cell_description: Series[str] = pa.Field(
        nullable=True, description="Free text cell line description"
    )
