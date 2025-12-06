"""Pandera schema for ChEMBL target data."""
import pandera as pa
from pandera.typing import Series

from bioetl.domain.transform.normalizers import (
    CHEMBL_ID_REGEX,
    UNIPROT_ID_REGEX,
)

OUTPUT_COLUMN_ORDER: list[str] = [
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
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
]


class TargetSchema(pa.DataFrameModel):
    """Schema for biological target data."""
    target_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern, description="ChEMBL ID таргета"
    )
    pref_name: Series[str] = pa.Field(
        nullable=True, description="Название таргета"
    )
    score: Series[float] = pa.Field(
        nullable=True, description="Score, используемый при поиске"
    )
    organism: Series[str] = pa.Field(nullable=True, description="Организм")
    target_type: Series[str] = pa.Field(
        description="Тип таргета (напр. SINGLE PROTEIN, FAMILY)"
    )
    tax_id: Series[float] = pa.Field(
        nullable=True, description="NCBI Taxonomy ID"
    )
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

    # Generated columns
    hash_row: Series[str] = pa.Field(
        str_matches=r"^[a-f0-9]{64}$", description="Хэш всей строки (64 hex)"
    )
    hash_business_key: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^[a-f0-9]{64}$",
        description="Хэш бизнес-ключа",
    )
    index: Series[int] = pa.Field(ge=0, description="Порядковый номер строки")
    database_version: Series[str] = pa.Field(nullable=True, description="Версия базы данных")
    extracted_at: Series[str] = pa.Field(nullable=True, description="Дата и время извлечения")

    class Config:
        """Pandera configuration."""

        strict = True
        coerce = True
        ordered = True
