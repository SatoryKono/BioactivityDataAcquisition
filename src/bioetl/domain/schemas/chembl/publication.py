"""Pandera schema for ChEMBL Publication entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.validation import (
    DOI_REGEX_PATTERN,
    MAX_PUBLICATION_YEAR,
    MIN_PUBLICATION_YEAR,
)


class ChemblPublicationSchema(ETLRecordSchema):
    """ChEMBL Publication validation schema for Silver layer."""

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
    # Cross-reference IDs for linking publications across providers
    # pmid: PubMed ID (numeric string: "12345678")
    pmid: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d+$",
        description="PubMed identifier (numeric string: '12345678').",
    )
    # pmc_id: PubMed Central ID (format: "PMC1234567")
    pmc_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
        description="PubMed Central identifier (format: 'PMC1234567').",
    )
    # doi: Digital Object Identifier (lowercase, without "https://doi.org/")
    doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX_PATTERN,
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
    year: Series[int] | None = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
        description="Publication year (1800-2100).",
    )
    volume: Series[str] | None = pa.Field(nullable=True, description="Volume.")
    issue: Series[str] | None = pa.Field(nullable=True, description="Issue.")
    first_page: Series[str] | None = pa.Field(nullable=True, description="First page.")
    last_page: Series[str] | None = pa.Field(nullable=True, description="Last page.")
    # ridx: Optional[Series[str]] = pa.Field(
    #     nullable=True, description="Record index."
    # )

    # === Lookup Metadata ===
    # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    # _original_id: Original identifier used for lookup (document_chembl_id for direct)
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=["direct", "doi", "pmid", "title_fallback", "unknown"],
        description="How record was resolved: direct for ChEMBL ID lookup",
    )

    original_id: Series[str] = pa.Field(
        alias="_original_id",
        nullable=True,
        description="Original identifier used for lookup (document_chembl_id)",
    )

    # === DQ Fields ===
    _dq_warn: Series[bool] = pa.Field(
        nullable=True, default=False, description="DQ warning flag."
    )
    _dq_error: Series[bool] = pa.Field(
        nullable=True, default=False, description="DQ error flag."
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
