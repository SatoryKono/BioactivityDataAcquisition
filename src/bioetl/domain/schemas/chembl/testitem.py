import pandera as pa
from typing import Any
from pandera.typing import Series


class TestitemSchema(pa.DataFrameModel):
    molecule_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$", description="ChEMBL ID молекулы")
    pref_name: Series[str] = pa.Field(nullable=True, description="Название молекулы")
    molecule_type: Series[str] = pa.Field(nullable=True, description="Тип молекулы (Small molecule, Antibody, etc.)")
    max_phase: Series[float] = pa.Field(nullable=True, description="Максимальная клиническая фаза")
    structure_type: Series[str] = pa.Field(nullable=True, description="Формат структуры (MOL, SMILES и т.п.)")
    molecule_properties: Series[str] = pa.Field(nullable=True, description="Свойства молекулы (например, логP, масса)")
    molecule_structures: Series[str] = pa.Field(nullable=True, description="Структурные данные (SMILES, InChI, молфайл)")
    molecule_hierarchy: Series[str] = pa.Field(nullable=True, description="Иерархия молекулы (родительская форма и пр.)")
    atc_classifications: Series[str] = pa.Field(nullable=True, description="Список ATC-классификаций")
    molecule_synonyms: Series[str] = pa.Field(nullable=True, description="Список синонимов")
    cross_references: Series[str] = pa.Field(nullable=True, description="Внешние кросс-референсы")
    helm_notation: Series[str] = pa.Field(nullable=True, description="HELM-нотация биотерапевтической молекулы")

    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$", description="Хэш всей строки (64 hex)")
    hash_business_key: Series[str] = pa.Field(nullable=True, str_matches=r"^[a-f0-9]{64}$", description="Хэш бизнес-ключа")

    class Config:
        strict = True
        coerce = True
