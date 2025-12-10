"""Pandera schema definitions for ChEMBL tissue dimension."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.chembl.base import (
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)
from bioetl.domain.transform.normalizers import CHEMBL_ID_REGEX

_TISSUE_BUSINESS_COLUMNS: list[str] = [
    "tissue_chembl_id",
    "tissue_name",
    "tissue_source_organism",
    "tissue_description",
    "tissue_type",
]

OUTPUT_COLUMN_ORDER: list[str] = build_output_column_order(_TISSUE_BUSINESS_COLUMNS)


class TissueTableSchema(BaseGeneratedColumnsSchema):
    """Normalized tissue reference table exported from ChEMBL."""

    tissue_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern,
        description="Primary ChEMBL tissue identifier",
    )
    tissue_name: Series[str] = pa.Field(
        nullable=True, description="Preferred tissue name"
    )
    tissue_source_organism: Series[str] = pa.Field(
        nullable=True, description="Organism the tissue sample originates from"
    )
    tissue_description: Series[str] = pa.Field(
        nullable=True, description="Free text describing tissue sample"
    )
    tissue_type: Series[str] = pa.Field(
        nullable=True, description="High-level tissue type or classification"
    )


__all__ = ["TissueTableSchema", "OUTPUT_COLUMN_ORDER"]
