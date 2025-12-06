"""Pandera schema for ChEMBL testitem/molecule data."""

import pandera as pa
from pandera.typing import Series

from bioetl.domain.transform.normalizers import (
    CHEMBL_ID_REGEX,
    PUBCHEM_CID_REGEX,
)


class TestitemSchema(pa.DataFrameModel):
    """Schema for molecule/test item data."""
    __test__ = False

    molecule_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern, description="ChEMBL ID молекулы"
    )
    pref_name: Series[str] = pa.Field(
        nullable=True, description="Название молекулы"
    )
    molecule_type: Series[str] = pa.Field(
        nullable=True,
        description="Тип молекулы (Small molecule, Antibody)",
    )
    max_phase: Series[float] = pa.Field(
        nullable=True, ge=0, le=4, description="Максимальная клиническая фаза"
    )
    structure_type: Series[str] = pa.Field(
        nullable=True, description="Формат структуры (MOL, SMILES и т.п.)"
    )
    molecule_properties: Series[str] = pa.Field(
        nullable=True, description="Свойства молекулы (например, логP, масса)"
    )
    molecule_structures: Series[str] = pa.Field(
        nullable=True,
        description="Структурные данные (SMILES, InChI)",
    )
    molecule_hierarchy: Series[str] = pa.Field(
        nullable=True,
        description="Иерархия молекулы (родительская форма)",
    )
    atc_classifications: Series[str] = pa.Field(
        nullable=True, description="Список ATC-классификаций"
    )
    molecule_synonyms: Series[str] = pa.Field(
        nullable=True, description="Список синонимов"
    )
    cross_references: Series[str] = pa.Field(
        nullable=True, description="Внешние кросс-референсы"
    )
    pubchem_cid: Series[str] = pa.Field(
        nullable=True,
        str_matches=PUBCHEM_CID_REGEX.pattern,
        description="PubChem Compound ID",
    )
    helm_notation: Series[str] = pa.Field(
        nullable=True, description="HELM-нотация биотерапевтической молекулы"
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
    database_version: Series[str] = pa.Field(
        nullable=True,
        description="Версия базы данных",
    )
    extracted_at: Series[str] = pa.Field(
        nullable=True,
        description="Дата и время извлечения",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        coerce = True
        ordered = True
