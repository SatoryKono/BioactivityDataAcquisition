"""
Activity Schema (Pandera).
"""
import pandera as pa
from pandera.typing import Series


class ActivitySchema(pa.DataFrameModel):
    """Схема данных для таблицы Activity."""

    activity_comment: Series[str] = pa.Field(nullable=True, description="Комментарий к активности")
    activity_id: Series[int] = pa.Field(ge=1, description="Внутренний ID активности")
    activity_properties: Series[str] = pa.Field(nullable=True, description="Список дополнительных свойств активности")
    assay_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$", description="ChEMBL ID ассая")
    assay_description: Series[str] = pa.Field(nullable=True, description="Текстовое описание ассая")
    assay_type: Series[str] = pa.Field(isin=["B", "F", "A", "T", "P", "U"], description="Тип ассая (B/F/A/T/P/U)")
    bao_endpoint: Series[str] = pa.Field(nullable=True, description="BAO endpoint term")
    bao_format: Series[str] = pa.Field(nullable=True, description="BAO format term")
    bao_label: Series[str] = pa.Field(nullable=True, description="Label для BAO endpoint/format")
    canonical_smiles: Series[str] = pa.Field(description="Канонический SMILES молекулы")
    data_validity_comment: Series[str] = pa.Field(nullable=True, description="Комментарий о качестве/валидности")
    data_validity_description: Series[str] = pa.Field(nullable=True, description="Описание проблем с данными")
    document_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$", description="ChEMBL ID документа-источника")
    document_journal: Series[str] = pa.Field(nullable=True, description="Название журнала")
    document_year: Series[float] = pa.Field(nullable=True, description="Год публикации")
    ligand_efficiency: Series[str] = pa.Field(nullable=True, description="Метрики эффективности Ligand Efficiency")
    molecule_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$", description="ChEMBL ID молекулы")
    molecule_pref_name: Series[str] = pa.Field(nullable=True, description="Название молекулы")
    parent_molecule_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID родительской молекулы")
    pchembl_value: Series[float] = pa.Field(nullable=True, ge=0, le=15, description="Нормализованная активность (-log10)")
    potential_duplicate: Series[bool] = pa.Field(nullable=True, description="Флаг потенциального дубликата")
    qudt_units: Series[str] = pa.Field(nullable=True, description="URI единиц (QUDT)")
    record_id: Series[float] = pa.Field(nullable=True, ge=1, description="ID связанной записи (compound_record)")
    relation: Series[str] = pa.Field(nullable=True, isin=["=", ">", "<", ">=", "<=", "~"], description="Исходное отношение (=, >, <, >=, <=, ~)")
    src_id: Series[float] = pa.Field(nullable=True, description="Источник данных (ID)")
    standard_flag: Series[bool] = pa.Field(description="Признак нормализации типа/значения")
    standard_relation: Series[str] = pa.Field(nullable=True, isin=["=", ">", "<", ">=", "<=", "~"], description="Нормализованное отношение")
    standard_text_value: Series[str] = pa.Field(nullable=True, description="Нормализованный текст для качественных значений")
    standard_type: Series[str] = pa.Field(nullable=True, description="Нормализованный тип активности")
    standard_units: Series[str] = pa.Field(nullable=True, description="Нормализованные единицы измерения")
    standard_upper_value: Series[float] = pa.Field(nullable=True, description="Верхняя граница нормализованного интервала")
    standard_value: Series[float] = pa.Field(nullable=True, description="Нормализованное числовое значение")
    target_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID таргета")
    target_organism: Series[str] = pa.Field(nullable=True, description="Организм таргета")
    target_pref_name: Series[str] = pa.Field(nullable=True, description="Название таргета")
    target_tax_id: Series[float] = pa.Field(nullable=True, description="NCBI TaxID таргета")
    text_value: Series[str] = pa.Field(nullable=True, description="Исходное текстовое значение")
    toid: Series[str] = pa.Field(nullable=True, description="ID из Target Ontology")
    type: Series[str] = pa.Field(nullable=True, description="Исходный тип активности (как в источнике)")
    units: Series[str] = pa.Field(nullable=True, description="Исходные единицы измерения")
    uo_units: Series[str] = pa.Field(nullable=True, description="ID единиц (Unit Ontology)")
    upper_value: Series[float] = pa.Field(nullable=True, description="Верхняя граница исходного интервала")
    value: Series[float] = pa.Field(nullable=True, description="Исходное числовое значение")

    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$", description="Хэш всей строки (64 hex символа)")
    hash_business_key: Series[str] = pa.Field(nullable=True, str_matches=r"^[a-f0-9]{64}$", description="Хэш бизнес-ключа (для идентификации дубликатов)")

    class Config:
        strict = True
        coerce = True
