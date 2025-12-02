import pandera as pa
from pandera.typing import Series


class AssaySchema(pa.DataFrameModel):
    assay_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$", description="ChEMBL ID ассая")
    assay_category: Series[str] = pa.Field(nullable=True, description="Категория ассая (primary/confirmatory/screening и т.п.)")
    assay_cell_type: Series[str] = pa.Field(nullable=True, description="Тип клеточной линии (если применимо)")
    assay_test_type: Series[str] = pa.Field(nullable=True, description="Тип теста (in vitro, in vivo, ex vivo и т.п.)")
    assay_tissue: Series[str] = pa.Field(nullable=True, description="Ткань, на которой проведён ассай")
    assay_type: Series[str] = pa.Field(isin=["B", "F", "A", "T", "P", "U"], description="Тип ассая (B – binding, F – functional и т.д.)")
    assay_type_description: Series[str] = pa.Field(nullable=True, description="Расшифровка типа ассая")
    cell_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID клеточной линии")
    confidence_score: Series[int] = pa.Field(nullable=True, ge=0, le=9, description="Уровень уверенности (0–9) в маппинге таргета")
    description: Series[str] = pa.Field(nullable=True, description="Описание теста")
    document_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID документа с описанием ассая")
    target_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID связанного таргета")
    tissue_chembl_id: Series[str] = pa.Field(nullable=True, str_matches=r"^CHEMBL\d+$", description="ChEMBL ID ткани")
    variant_sequence: Series[str] = pa.Field(nullable=True, description="Последовательность варианта (если таргет – белок)")

    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$", description="Хэш всей строки (64 hex)")
    hash_business_key: Series[str] = pa.Field(nullable=True, str_matches=r"^[a-f0-9]{64}$", description="Хэш бизнес-идентификатора ассая")

    class Config:
        strict = True
        coerce = True
