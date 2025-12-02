import pandera as pa
from pandera.typing import Series

from bioetl.domain.transform.custom_types import CHEMBL_ID_REGEX, UNIPROT_ID_REGEX


class TargetSchema(pa.DataFrameModel):
    target_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern, description="ChEMBL ID таргета"
    )
    pref_name: Series[str] = pa.Field(nullable=True, description="Название таргета")
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

    # Generated columns
    hash_row: Series[str] = pa.Field(
        str_matches=r"^[a-f0-9]{64}$", description="Хэш всей строки (64 hex)"
    )
    hash_business_key: Series[str] = pa.Field(
        nullable=True, str_matches=r"^[a-f0-9]{64}$", description="Хэш бизнес-ключа"
    )

    class Config:
        strict = True
        coerce = True
