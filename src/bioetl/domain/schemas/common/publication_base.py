"""Base schema for all publication entities across providers.

Aligned with RULES.md v5.10 and Publication Schema Unification spec.
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

# Lookup method values (used by ChEMBL, OpenAlex, SemanticScholar)
LOOKUP_METHODS = ["direct", "doi", "pmid", "title_fallback", "title_only", "unknown"]


class PublicationBaseSchema(ETLRecordSchema):
    """Base schema with common fields for all publication entities.

    Provider-specific schemas inherit from this and add their own fields.
    Only fields common to ALL providers are defined here.
    """

    # === Cross-reference IDs (common to all providers) ===
    # Note: PubMed overrides pmid to be int type instead of str
    pmid: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d+$",
        description="PubMed ID (numeric string)",
    )
    doi: Series[str] = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX_PATTERN,
        description="Digital Object Identifier (lowercase)",
    )
    pmc_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
        description="PubMed Central ID",
    )

    # === Core content (common to all providers) ===
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)

    # === Publication metadata (common to all providers) ===
    year: Series[int] = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow extra columns
        ordered = False
        coerce = True
