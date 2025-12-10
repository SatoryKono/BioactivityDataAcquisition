"""Pandera schema for ChEMBL target data."""

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.chembl.base import (
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)
from bioetl.domain.transform.normalizers import (
    CHEMBL_ID_REGEX,
    UNIPROT_ID_REGEX,
)

_TARGET_BUSINESS_COLUMNS: list[str] = [
    "target_chembl_id",
    "pref_name",
    "score",
    "organism",
    "target_type",
    "tax_id",
    "species_group_flag",
    "target_components",
    "cross_references",
    "uniprot_id",
]

OUTPUT_COLUMN_ORDER: list[str] = build_output_column_order(_TARGET_BUSINESS_COLUMNS)


class TargetTableSchema(BaseGeneratedColumnsSchema):
    """Schema for biological target table (pipeline output)."""

    target_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern, description="ChEMBL ID таргета"
    )
    pref_name: Series[str] = pa.Field(nullable=True, description="Название таргета")
    score: Series[float] = pa.Field(
        nullable=True, description="Score, используемый при поиске"
    )
    organism: Series[str] = pa.Field(nullable=True, description="Организм")
    target_type: Series[str] = pa.Field(
        description="Тип таргета (напр. SINGLE PROTEIN, FAMILY)"
    )
    tax_id: Series[float] = pa.Field(nullable=True, description="NCBI Taxonomy ID")
    species_group_flag: Series[bool] = pa.Field(
        nullable=True, description="Флаг группового таргета по видам"
    )
    target_components: Series[str] = pa.Field(
        nullable=True, description="Список компонентов таргета"
    )
    cross_references: Series[str] = pa.Field(
        nullable=True, description="Внешние кросс-референсы"
    )
    uniprot_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=UNIPROT_ID_REGEX.pattern,
        description="Основной UniProt ID",
    )


__all__ = ["TargetTableSchema", "OUTPUT_COLUMN_ORDER"]
