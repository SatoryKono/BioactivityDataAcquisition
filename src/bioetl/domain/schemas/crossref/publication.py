"""Pandera schema for CrossRef Publication (enriched) entity.

Used for Silver layer validation of publications enriched via CrossRef API.
Aligned with RULES.md v5.10.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import PublicationBaseSchema
from bioetl.domain.validation import DOI_REGEX_PATTERN

# === Fixed Value Constants ===
DOCUMENT_TYPES = ["PUBLICATION", "PREPRINT"]


class PublicationEnrichedSchema(PublicationBaseSchema):
    """CrossRef-enriched Publication validation schema for Silver layer.

    Represents publication metadata from CrossRef API with citation enrichment.
    """

    # === Primary Key (override doi to be non-nullable) ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=DOI_REGEX_PATTERN,
        description="Digital Object Identifier (normalized: lowercase, stripped)",
    )

    # === Provider-specific Fields ===
    issn: Series[str] = pa.Field(
        nullable=True, description="JSON array of ISSNs"
    )
    publisher: Series[str] = pa.Field(
        nullable=True, description="Publisher name"
    )

    # === Dates (CrossRef-specific) ===
    published_print: Series[str] = pa.Field(
        nullable=True, description="Print publication date (ISO format)"
    )
    published_online: Series[str] = pa.Field(
        nullable=True, description="Online publication date (ISO format)"
    )

    # === Override doc_type with CrossRef-specific values ===
    doc_type: Series[str] = pa.Field(
        nullable=False,
        isin=DOCUMENT_TYPES,
        description="Document type: PUBLICATION or PREPRINT",
    )

    # === Additional Metadata ===
    language: Series[str] = pa.Field(
        nullable=True, description="Publication language code"
    )
    license_url: Series[str] = pa.Field(nullable=True, description="License URL")
    subjects: Series[str] = pa.Field(
        nullable=True, description="JSON array of subject areas"
    )

    # === Source Tracking ===
    source: Series[str] = pa.Field(
        nullable=False, eq="crossref", description="Data source identifier"
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        ordered = False  # Changed to False for inheritance compatibility
        coerce = True
        name = "PublicationEnrichedSchema"
        description = "CrossRef-enriched Publication Silver layer validation"
