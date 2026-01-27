"""Pandera schema for OpenAlex Publication entity.

Aligned with RULES.md v5.10 and Publication Schema Unification spec.
Includes lookup metadata fields for DOI/title resolution tracking.

Topics vs Concepts (2024 Migration):
- OpenAlex deprecated the `concepts` field in 2024 in favor of `topics`
- Topics provide a 4-level hierarchy: domain -> field -> subfield -> topic
- The `concepts` field is kept for backward compatibility during transition
- New code should use `topics` and `primary_topic` fields
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    OA_STATUS_VALUES,
    PublicationBaseSchema,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = [
    "DOI_REGEX_PATTERN",
    "LOOKUP_METHODS",
    "OA_STATUS_VALUES",
    "OpenAlexPublicationSchema",
]


class OpenAlexPublicationSchema(PublicationBaseSchema):
    """OpenAlex Publication validation schema for Silver layer.

    Validates publication records from OpenAlex Works API.
    Inherits common fields from PublicationBaseSchema:
    - Cross-references: pmid, doi, pmc_id
    - Core content: title, abstract, authors
    - Metadata: journal, year (overridden), publication_date, doc_type (overridden), language
    - Metrics: citation_count (overridden for nullable int)
    - Open Access: is_oa
    - Lookup tracking: lookup_method (overridden), original_id, source (overridden)
    """

    # === Primary Key (OpenAlex-specific) ===
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
        description="OpenAlex Work ID (e.g., W2148763428)",
    )

    # === Override lookup_method to be non-nullable ===
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: doi, title_fallback, title_only",
    )

    # === Override year with pd.Int64Dtype for nullable int ===
    year: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=1800,
        le=2100,
        description="Publication year (1800-2100).",
    )

    # === Override doc_type to be non-nullable ===
    doc_type: Series[str] = pa.Field(
        nullable=False,
        description="Publication type (PUBLICATION, PREPRINT, etc.)",
    )

    # === Override citation_count with pd.Int64Dtype for nullable int ===
    citation_count: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of citations (from OpenAlex cited_by_count).",
    )

    # === Override _source to be non-nullable ===
    _source: Series[str] = pa.Field(
        nullable=False,
        description="Data source identifier",
    )

    # === Provider-specific Fields ===
    issn: Series[str] = pa.Field(
        nullable=True,
        description="ISSN-L",
    )

    publisher: Series[str] = pa.Field(
        nullable=True,
        description="Publisher name",
    )

    oa_status: Series[str] = pa.Field(
        nullable=True,
        isin=OA_STATUS_VALUES,
        description="OA status (gold, green, hybrid, bronze, closed)",
    )

    # === Bibliographic Info (from biblio object) ===
    volume: Series[str] = pa.Field(
        nullable=True,
        description="Journal volume number",
    )

    issue: Series[str] = pa.Field(
        nullable=True,
        description="Journal issue number",
    )

    # === Additional Metrics ===
    fwci: Series[float] = pa.Field(
        nullable=True,
        ge=0,
        description="Field-Weighted Citation Impact (must be non-negative)",
    )

    referenced_works_count: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of works referenced (must be non-negative)",
    )

    # === Quality Indicators ===
    is_retracted: Series[bool] = pa.Field(
        nullable=False,
        description="Whether the publication has been retracted",
    )

    # === Topics (hierarchical classification - replaces deprecated concepts) ===
    # Stored as JSON-serialized string for DataFrame compatibility
    topics: Series[str] = pa.Field(
        nullable=True,
        description="Hierarchical topic classification (JSON array)",
    )

    # Primary topic (single most relevant topic for quick categorization)
    # Stored as JSON-serialized string for DataFrame compatibility
    primary_topic: Series[str] = pa.Field(
        nullable=True,
        description="Primary topic classification (JSON object)",
    )

    # === Grants/Funding Information ===
    # Stored as JSON-serialized string for DataFrame compatibility
    grants: Series[str] = pa.Field(
        nullable=True,
        description="Funding/grant information (JSON array)",
    )

    # === Classification Fields (extracted by transformer) ===
    concepts: Series[str] = pa.Field(
        nullable=True,
        description="OpenAlex concepts (JSON array, DEPRECATED: use topics)",
    )

    mesh: Series[str] = pa.Field(
        nullable=True,
        description="MeSH terms (JSON array of descriptor names)",
    )

    keywords: Series[str] = pa.Field(
        nullable=True,
        description="Keywords (JSON array)",
    )

    # === External Identifier ===
    mag_id: Series[str] = pa.Field(
        nullable=True,
        description="Microsoft Academic Graph ID (legacy)",
    )

    # === Bibliographic Page Info ===
    first_page: Series[str] = pa.Field(
        nullable=True,
        description="First page number (from biblio object)",
    )

    last_page: Series[str] = pa.Field(
        nullable=True,
        description="Last page number (from biblio object)",
    )

    # === Author Affiliations ===
    affiliations: Series[str] = pa.Field(
        nullable=True,
        description="Author affiliations (JSON array)",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        coerce = True  # Coerce data types to match schema
