import pandera as pa
from pandera.typing import Series


class AssaySchema(pa.DataFrameModel):
    aidx: Series[str] = pa.Field(nullable=True, description="Внутренний индекс ассая/ID депозитора")
    assay_category: Series[str] = pa.Field(nullable=True, description="Категория ассая (primary/confirmatory/screening и т.п.)")
    assay_cell_type: Series[str] = pa.Field(nullable=True, description="Тип клеточной линии (если применимо)")
    assay_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$", description="ChEMBL ID ассая")
    assay_classifications: Series[str] = pa.Field(nullable=True, description="Классификации ассая (BAO и др.)")
    assay_group: Series[str] = pa.Field(nullable=True, description="Группа/серия, к которой относится тест")
    assay_organism: Series[str] = pa.Field(nullable=True, description="Организм системы тестирования")
    assay_parameters: Series[str] = pa.Field(nullable=True, description="Параметры теста")
    assay_strain: Series[str] = pa.Field(nullable=True, description="Штамм организма")
    assay_subcellular_fraction: Series[str] = pa.Field(nullable=True, description="Субклеточная фракция")
    assay_tax_id: Series[float] = pa.Field(nullable=True, description="NCBI Taxonomy ID организма")
    assay_test_type: Series[str] = pa.Field(nullable=True, description="Тип теста (in vitro, in vivo, ex vivo и т.п.)")
    assay_tissue: Series[str] = pa.Field(nullable=True, description="Ткань, на которой проведён ассай")
    assay_type: Series[str] = pa.Field(isin=["B", "F", "A", "T", "P", "U"], description="Тип ассая (B – binding, F – functional и т.д.)")
    assay_type_description: Series[str] = pa.Field(nullable=True, description="Расшифровка типа ассая")
    bao_format: Series[str] = pa.Field(nullable=True, description="BAO формат ассая")
    bao_label: Series[str] = pa.Field(nullable=True, description="Читабельная метка BAO-формата")
    cell_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID клеточной линии")
    confidence_description: Series[str] = pa.Field(nullable=True, description="Текстовое описание уровня уверенности")
    confidence_score: Series[int] = pa.Field(nullable=True, ge=0, le=9, description="Уровень уверенности (0–9) в маппинге таргета")
    description: Series[str] = pa.Field(nullable=True, description="Описание теста")
    document_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID документа с описанием ассая")
    relationship_description: Series[str] = pa.Field(nullable=True, description="Расшифровка relationship_type")
    relationship_type: Series[str] = pa.Field(nullable=True, description="Тип связи ассая с таргетом")
    score: Series[float] = pa.Field(nullable=True, description="Score для ранжирования ассая при поиске")
    src_assay_id: Series[str] = pa.Field(nullable=True, description="Идентификатор ассая в исходной БД")
    src_id: Series[float] = pa.Field(nullable=True, description="ID источника данных")
    target_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID связанного таргета")
    tissue_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID ткани")
    variant_sequence: Series[str] = pa.Field(nullable=True, description="Последовательность варианта (если таргет – белок)")

    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$", description="Хэш всей строки (64 hex)")
    hash_business_key: Series[str] = pa.Field(nullable=True, str_matches=r"^[a-f0-9]{64}$", description="Хэш бизнес-идентификатора ассая")
    index: Series[int] = pa.Field(ge=0, description="Порядковый номер строки")
    database_version: Series[str] = pa.Field(nullable=True, description="Версия базы данных")
    extracted_at: Series[str] = pa.Field(nullable=True, description="Дата и время извлечения")

    class Config:
        strict = True
        coerce = True
