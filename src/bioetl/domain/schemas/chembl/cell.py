"""Pandera schema definitions for ChEMBL cell dimension."""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.chembl.base import BaseGeneratedColumnsSchema
from bioetl.domain.transform.normalizers import CHEMBL_ID_REGEX


class CellTableSchema(BaseGeneratedColumnsSchema):
    """Normalized cell reference table exported from ChEMBL."""

    cell_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern,
        description="Primary ChEMBL cell identifier",
    )
    cell_name: Series[str] = pa.Field(
        nullable=True, description="Preferred cell line name provided by ChEMBL"
    )
    cell_source_organism: Series[str] = pa.Field(
        nullable=True, description="Organism or lineage the cell line originates from"
    )
    cell_type: Series[str] = pa.Field(
        nullable=True, description="High-level cell type (epithelial, stem, etc.)"
    )
    cell_description: Series[str] = pa.Field(
        nullable=True, description="Free text notes describing the cell line"
    )


__all__ = ["CellTableSchema"]
