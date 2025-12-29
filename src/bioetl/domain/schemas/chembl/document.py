"""Pandera schema for ChEMBL Document entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class DocumentSchema(ETLRecordSchema):
    """Document validation schema for Silver layer."""

    # === Primary Key ===
    # doc_id: Series[int] = pa.Field(
    #     nullable=False, description="Primary key."
    # )
    # Removed doc_id as it is not in Silver schema. document_chembl_id is the PK.

    # === Identifiers ===
    document_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID.",
    )
    pubmed_id: Series[int] | None = pa.Field(nullable=True, description="PubMed ID.")
    doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^10\.\d+/.+$",
        description="DOI.",
    )
    patent_id: Series[str] | None = pa.Field(nullable=True, description="Patent ID.")
    src_id: Series[int] | None = pa.Field(nullable=True, description="Source ID.")

    # === Metadata ===
    title: Series[str] | None = pa.Field(nullable=True, description="Title.")
    doc_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["PUBLICATION", "PATENT", "DATASET", "BOOK"],
        description="Document type.",
    )
    authors: Series[str] | None = pa.Field(nullable=True, description="Authors.")
    abstract: Series[str] | None = pa.Field(nullable=True, description="Abstract.")
    journal: Series[str] | None = pa.Field(nullable=True, description="Journal.")
    journal_full_title: Series[str] | None = pa.Field(
        nullable=True, description="Full journal title."
    )
    year: Series[int] | None = pa.Field(nullable=True, description="Year.")
    volume: Series[str] | None = pa.Field(nullable=True, description="Volume.")
    issue: Series[str] | None = pa.Field(nullable=True, description="Issue.")
    first_page: Series[str] | None = pa.Field(nullable=True, description="First page.")
    last_page: Series[str] | None = pa.Field(nullable=True, description="Last page.")
    # ridx: Optional[Series[str]] = pa.Field(
    #     nullable=True, description="Record index."
    # )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
