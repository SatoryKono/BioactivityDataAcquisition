"""
Activity Schema (Pandera).
"""
import pandera as pa
from pandera.typing import Series

from bioetl.domain.transform.normalizers import BAO_ID_REGEX, CHEMBL_ID_REGEX

OUTPUT_COLUMN_ORDER: list[str] = [
    "action_type",
    "activity_comment",
    "activity_id",
    "activity_properties",
    "assay_chembl_id",
    "assay_description",
    "assay_type",
    "assay_variant_accession",
    "assay_variant_mutation",
    "bao_endpoint",
    "bao_format",
    "bao_label",
    "canonical_smiles",
    "data_validity_comment",
    "data_validity_description",
    "document_chembl_id",
    "document_journal",
    "document_year",
    "ligand_efficiency",
    "molecule_chembl_id",
    "molecule_pref_name",
    "parent_molecule_chembl_id",
    "pchembl_value",
    "potential_duplicate",
    "qudt_units",
    "record_id",
    "relation",
    "src_id",
    "standard_flag",
    "standard_relation",
    "standard_text_value",
    "standard_type",
    "standard_units",
    "standard_upper_value",
    "standard_value",
    "target_chembl_id",
    "target_organism",
    "target_pref_name",
    "target_tax_id",
    "text_value",
    "toid",
    "type",
    "units",
    "uo_units",
    "upper_value",
    "value",
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
]


class ActivitySchema(pa.DataFrameModel):
    """Схема данных для таблицы Activity."""

    action_type: Series[str] = pa.Field(nullable=True, description="Тип действия (agonist, antagonist)")
    activity_comment: Series[str] = pa.Field(nullable=True, description="Комментарий к активности")
    activity_id: Series[int] = pa.Field(ge=1, description="Внутренний ID активности")
    activity_properties: Series[str] = pa.Field(nullable=True, description="Список дополнительных свойств активности")
    assay_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern, description="ChEMBL ID ассая"
    )
    assay_description: Series[str] = pa.Field(nullable=True, description="Текстовое описание ассая")
    assay_type: Series[str] = pa.Field(isin=["B", "F", "A", "T", "P", "U"], description="Тип ассая (B/F/A/T/P/U)")
    assay_variant_accession: Series[str] = pa.Field(nullable=True, description="Accession варианта белка")
    assay_variant_mutation: Series[str] = pa.Field(nullable=True, description="Описание мутаций варианта белка")
    bao_endpoint: Series[str] = pa.Field(
        nullable=True,
        str_matches=BAO_ID_REGEX.pattern,
        description="BAO endpoint term",
    )
    bao_format: Series[str] = pa.Field(
        nullable=True,
        str_matches=BAO_ID_REGEX.pattern,
        description="BAO format term",
    )
    bao_label: Series[str] = pa.Field(nullable=True, description="Label для BAO endpoint/format")
    canonical_smiles: Series[str] = pa.Field(nullable=True, description="Канонический SMILES молекулы")
    data_validity_comment: Series[str] = pa.Field(nullable=True, description="Комментарий о качестве/валидности")
    data_validity_description: Series[str] = pa.Field(nullable=True, description="Описание проблем с данными")
    document_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern, description="ChEMBL ID документа-источника"
    )
    document_journal: Series[str] = pa.Field(nullable=True, description="Название журнала")
    document_year: Series[float] = pa.Field(nullable=True, description="Год публикации")
    ligand_efficiency: Series[str] = pa.Field(nullable=True, description="Метрики эффективности Ligand Efficiency")
    molecule_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern, description="ChEMBL ID молекулы"
    )
    molecule_pref_name: Series[str] = pa.Field(nullable=True, description="Название молекулы")
    parent_molecule_chembl_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_REGEX.pattern,
        description="ChEMBL ID родительской молекулы",
    )
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
    target_chembl_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_REGEX.pattern,
        description="ChEMBL ID таргета",
    )
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
    index: Series[int] = pa.Field(ge=0, description="Порядковый номер строки")
    database_version: Series[str] = pa.Field(nullable=True, description="Версия базы данных")
    extracted_at: Series[str] = pa.Field(nullable=True, description="Дата и время извлечения")

    class Config:
        strict = True
        coerce = True
        ordered = True
