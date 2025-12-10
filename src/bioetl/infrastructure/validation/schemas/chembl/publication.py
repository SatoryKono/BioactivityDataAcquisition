"""Pandera schema for ChEMBL publication data.

This schema validates the structure and content of publication/document data
after normalization.
"""

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.field_specs import (
    CHEMBL_ID_PATTERN,
    DOI_PATTERN,
    PUBMED_ID_PATTERN,
)
from bioetl.infrastructure.validation.schemas.pandera_base import (
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)

__all__ = ["PublicationTableSchema", "OUTPUT_COLUMN_ORDER"]

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

OUTPUT_COLUMN_ORDER: list[str] = build_output_column_order(
    _PUBLICATION_BUSINESS_COLUMNS
)


class PublicationTableSchema(BaseGeneratedColumnsSchema):
    """Schema for publication table (pipeline output).

    Validates ChEMBL document records including:
    - Publication metadata (journal, authors, year)
    - External identifiers (DOI, PubMed ID)
    - Document types and classifications
    """

    abstract: Series[str] = pa.Field(nullable=True, description="Document abstract")
    authors: Series[str] = pa.Field(nullable=True, description="List of authors")
    chembl_release: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL release when document appeared",
    )
    contact: Series[str] = pa.Field(
        nullable=True, description="Contact for deposited datasets"
    )
    doc_type: Series[str] = pa.Field(
        isin=["PUBLICATION", "DATASET", "PATENT", "OTHER"],
        description="Document type",
    )
    document_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_PATTERN, description="ChEMBL document identifier"
    )
    doi: Series[str] = pa.Field(
        nullable=True,
        str_matches=DOI_PATTERN,
        description="DOI (normalized)",
    )
    doi_chembl: Series[str] = pa.Field(
        nullable=True, description="Internal ChEMBL DOI for datasets"
    )
    first_page: Series[str] = pa.Field(nullable=True, description="First page number")
    issue: Series[str] = pa.Field(nullable=True, description="Journal issue number")
    journal: Series[str] = pa.Field(
        nullable=True, description="Abbreviated journal name"
    )
    journal_full_title: Series[str] = pa.Field(
        nullable=True, description="Full journal title"
    )
    last_page: Series[str] = pa.Field(nullable=True, description="Last page number")
    patent_id: Series[str] = pa.Field(
        nullable=True, description="Patent identifier"
    )
    pubmed_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=PUBMED_ID_PATTERN,
        description="PubMed ID",
    )
    score: Series[float] = pa.Field(
        nullable=True, description="Search ranking score"
    )
    src_id: Series[float] = pa.Field(
        nullable=True,
        description="Data source ID",
    )
    title: Series[str] = pa.Field(nullable=True, description="Document title")
    volume: Series[str] = pa.Field(nullable=True, description="Journal volume")
    year: Series[float] = pa.Field(nullable=True, description="Publication year")
