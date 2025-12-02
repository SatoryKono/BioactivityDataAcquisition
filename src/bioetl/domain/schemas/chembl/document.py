import pandera as pa
from pandera.typing import Series

from bioetl.domain.transform.impl.normalize import DOI_REGEX


class DocumentSchema(pa.DataFrameModel):
    abstract: Series[str] = pa.Field(nullable=True, description="Аннотация документа")
    authors: Series[str] = pa.Field(nullable=True, description="Список авторов")
    doc_type: Series[str] = pa.Field(
        isin=["PUBLICATION", "DATASET", "PATENT", "OTHER"],
        description="Тип документа",
    )
    document_chembl_id: Series[str] = pa.Field(
        str_matches=r"^CHEMBL\d+$", description="ChEMBL ID документа"
    )
    doi: Series[str] = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX.pattern,
        description="DOI публикации",
    )
    doi_clean: Series[str] = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX.pattern,
        description="Нормализованный DOI",
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
    last_page: Series[str] = pa.Field(
        nullable=True, description="Последняя страница"
    )
    patent_id: Series[str] = pa.Field(
        nullable=True, description="Идентификатор патента"
    )
    pubmed_id: Series[int] = pa.Field(
        nullable=True,
        description="PubMed ID",
    )
    src_id: Series[float] = pa.Field(
        nullable=True,
        description="ID источника данных",
    )
    title: Series[str] = pa.Field(nullable=True, description="Заголовок документа")
    volume: Series[str] = pa.Field(nullable=True, description="Том выпуска")
    year: Series[float] = pa.Field(nullable=True, description="Год публикации")
    chembl_release: Series[str] = pa.Field(
        nullable=True,
        description="ID релиза ChEMBL появления документа",
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

    class Config:
        strict = True
        coerce = True
