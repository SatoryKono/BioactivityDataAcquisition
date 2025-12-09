"""Pandera schema for ChEMBL publication data."""

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.chembl.base import (
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)
from bioetl.domain.transform.normalizers import (
    CHEMBL_ID_REGEX,
    DOI_REGEX,
    PUBMED_ID_REGEX,
)

_PUBLICATION_BUSINESS_COLUMNS: list[str] = [
    "abstract",
    "authors",
    "chembl_release",
    "contact",
    "doc_type",
    "document_chembl_id",
    "doi",
    "doi_chembl",
    "first_page",
    "issue",
    "journal",
    "journal_full_title",
    "last_page",
    "patent_id",
    "pubmed_id",
    "score",
    "src_id",
    "title",
    "volume",
    "year",
]

OUTPUT_COLUMN_ORDER: list[str] = build_output_column_order(_PUBLICATION_BUSINESS_COLUMNS)


class PublicationTableSchema(BaseGeneratedColumnsSchema):
    """Schema for publication table (pipeline output)."""

    abstract: Series[str] = pa.Field(nullable=True, description="Аннотация документа")
    authors: Series[str] = pa.Field(nullable=True, description="Список авторов")
    chembl_release: Series[str] = pa.Field(
        nullable=True,
        description="ID релиза ChEMBL появления документа",
    )
    contact: Series[str] = pa.Field(
        nullable=True, description="Контакт для deposited datasets"
    )
    doc_type: Series[str] = pa.Field(
        isin=["PUBLICATION", "DATASET", "PATENT", "OTHER"],
        description="Тип документа",
    )
    document_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern, description="ChEMBL ID документа"
    )
    doi: Series[str] = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX.pattern,
        description="DOI публикации (нормализован)",
    )
    doi_chembl: Series[str] = pa.Field(
        nullable=True, description="Внутренний DOI ChEMBL (для датасетов)"
    )
    first_page: Series[str] = pa.Field(nullable=True, description="Первая страница")
    issue: Series[str] = pa.Field(nullable=True, description="Номер выпуска журнала")
    journal: Series[str] = pa.Field(
        nullable=True, description="Сокращенное название журнала"
    )
    journal_full_title: Series[str] = pa.Field(
        nullable=True, description="Полное название журнала"
    )
    last_page: Series[str] = pa.Field(nullable=True, description="Последняя страница")
    patent_id: Series[str] = pa.Field(
        nullable=True, description="Идентификатор патента"
    )
    pubmed_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=PUBMED_ID_REGEX.pattern,
        description="PubMed ID",
    )
    score: Series[float] = pa.Field(
        nullable=True, description="Score для поискового ранжирования"
    )
    src_id: Series[float] = pa.Field(
        nullable=True,
        description="ID источника данных",
    )
    title: Series[str] = pa.Field(nullable=True, description="Заголовок документа")
    volume: Series[str] = pa.Field(nullable=True, description="Том выпуска")
    year: Series[float] = pa.Field(nullable=True, description="Год публикации")


__all__ = ["PublicationTableSchema", "OUTPUT_COLUMN_ORDER"]
