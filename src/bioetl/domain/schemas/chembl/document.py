"""Pandera schema for ChEMBL Document entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class DocumentSchema(ETLRecordSchema):
    """Document validation schema for Silver/Gold layers."""

    # === Primary Key ===
    document_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="Primary key (ChEMBL identifier).",
    )

    # === External Identifiers ===
    pubmed_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="PubMed ID."
    )
    doi: Optional[Series[str]] = pa.Field(
        nullable=True, description="Digital Object Identifier."
    )
    patent_id: Optional[Series[str]] = pa.Field(
        nullable=True, description="Patent ID."
    )

    # === Core Metadata ===
    title: Optional[Series[str]] = pa.Field(
        nullable=True, description="Document title."
    )
    doc_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["PUBLICATION", "PATENT", "DATASET", "BOOK"],
        description="Document type.",
    )
    authors: Optional[Series[str]] = pa.Field(
        nullable=True, description="Authors string."
    )
    abstract: Optional[Series[str]] = pa.Field(
        nullable=True, description="Abstract text."
    )

    # === Journal Information ===
    journal: Optional[Series[str]] = pa.Field(
        nullable=True, description="Journal name."
    )
    journal_full_title: Optional[Series[str]] = pa.Field(
        nullable=True, description="Full journal title."
    )
    year: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1800,
        le=2100,
        description="Publication year.",
    )
    volume: Optional[Series[str]] = pa.Field(
        nullable=True, description="Journal volume."
    )
    issue: Optional[Series[str]] = pa.Field(
        nullable=True, description="Journal issue."
    )
    first_page: Optional[Series[str]] = pa.Field(
        nullable=True, description="First page."
    )
    last_page: Optional[Series[str]] = pa.Field(
        nullable=True, description="Last page."
    )
    src_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Source ID."
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = False
        coerce = True
