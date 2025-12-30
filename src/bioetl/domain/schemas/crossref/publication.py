"""Pandera schema for CrossRef Publication (enriched) entity.

Used for Silver layer validation of publications enriched via CrossRef API.
Aligned with RULES.md v5.8.
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
DOCUMENT_TYPES = ["PUBLICATION", "PREPRINT"]


class PublicationEnrichedSchema(ETLRecordSchema):
    """CrossRef-enriched Publication validation schema for Silver layer.

    Represents publication metadata from CrossRef API with citation enrichment.
    """

    # === Primary Key (DOI) ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^10\.\d{4,}/.+$",
        description="Digital Object Identifier (normalized: lowercase, stripped)",
    )

    # === Core Metadata ===
    title: Series[str] | None = pa.Field(
        nullable=True,
        str_length={"min_value": 1},
        description="Publication title (first title from CrossRef)",
    )
    abstract: Series[str] | None = pa.Field(
        nullable=True, description="Abstract text (HTML tags stripped)"
    )

    # === Authors ===
    authors: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of author names in 'given family' format",
    )

    # === Journal Information ===
    journal: Series[str] | None = pa.Field(
        nullable=True, description="Journal name (container-title[0])"
    )
    issn: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of ISSNs"
    )
    publisher: Series[str] | None = pa.Field(
        nullable=True, description="Publisher name"
    )

    # === Publication Details ===
    volume: Series[str] | None = pa.Field(nullable=True, description="Journal volume")
    issue: Series[str] | None = pa.Field(nullable=True, description="Journal issue")
    first_page: Series[str] | None = pa.Field(
        nullable=True, description="First page (extracted from 'page' field)"
    )
    last_page: Series[str] | None = pa.Field(
        nullable=True, description="Last page (extracted from 'page' field)"
    )

    # === Dates ===
    year: Series[int] | None = pa.Field(
        nullable=True, ge=1800, le=2100, description="Publication year"
    )
    published_print: Series[str] | None = pa.Field(
        nullable=True, description="Print publication date (ISO format)"
    )
    published_online: Series[str] | None = pa.Field(
        nullable=True, description="Online publication date (ISO format)"
    )

    # === Document Type ===
    doc_type: Series[str] = pa.Field(
        nullable=False,
        isin=DOCUMENT_TYPES,
        description="Document type: PUBLICATION or PREPRINT",
    )

    # === Citation Metrics ===
    citation_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of citations (is-referenced-by-count)",
    )
    reference_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of references in the work"
    )

    # === Additional Metadata ===
    language: Series[str] | None = pa.Field(
        nullable=True, description="Publication language code"
    )
    license_url: Series[str] | None = pa.Field(nullable=True, description="License URL")
    subjects: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of subject areas"
    )

    # === Source Tracking ===
    source: Series[str] = pa.Field(
        nullable=False, eq="crossref", description="Data source identifier"
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "PublicationEnrichedSchema"
        description = "CrossRef-enriched Publication Silver layer validation"
