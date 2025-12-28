"""Pandera schema for ChEMBL Document entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class DocumentSchema(ETLRecordSchema):
    """Document validation schema for Silver layer."""

    # === Primary Key ===
    doc_id: Series[int] = pa.Field(
        nullable=False, description="Primary key."
    )

    # === Identifiers ===
    document_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID.",
    )
    pubmed_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="PubMed ID."
    )
    doi: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^10\.\d+/.+$",
        description="DOI.",
    )
    patent_id: Optional[Series[str]] = pa.Field(
        nullable=True, description="Patent ID."
    )
    src_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Source ID."
    )

    # === Metadata ===
    title: Optional[Series[str]] = pa.Field(
        nullable=True, description="Title."
    )
    doc_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["PUBLICATION", "PATENT", "DATASET", "BOOK"],
        description="Document type.",
    )
    authors: Optional[Series[str]] = pa.Field(
        nullable=True, description="Authors."
    )
    abstract: Optional[Series[str]] = pa.Field(
        nullable=True, description="Abstract."
    )
    journal: Optional[Series[str]] = pa.Field(
        nullable=True, description="Journal."
    )
    year: Optional[Series[int]] = pa.Field(
        nullable=True, description="Year."
    )
    volume: Optional[Series[str]] = pa.Field(
        nullable=True, description="Volume."
    )
    issue: Optional[Series[str]] = pa.Field(
        nullable=True, description="Issue."
    )
    first_page: Optional[Series[str]] = pa.Field(
        nullable=True, description="First page."
    )
    last_page: Optional[Series[str]] = pa.Field(
        nullable=True, description="Last page."
    )
    ridx: Optional[Series[str]] = pa.Field(
        nullable=True, description="Record index."
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
