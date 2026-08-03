"""Pandera schema for OpenAlex Publication entity.

Aligned with RULES.md v5.24 and Publication Schema Unification spec.
Includes lookup metadata fields for DOI/title resolution tracking.

Topics provide a 4-level hierarchy: domain -> field -> subfield -> topic.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    OA_STATUS_VALUES,
    PublicationBaseSchema,
)
from bioetl.domain.schemas.constants import ISSN_PATTERN
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = [
    "DOI_REGEX_PATTERN",
    "OA_STATUS_VALUES",
    "OpenAlexPublicationSchema",
]


class OpenAlexPublicationSchema(PublicationBaseSchema):
    """OpenAlex Publication validation schema for Silver layer.

    Validates publication records from OpenAlex Works API.
    Inherits common fields from PublicationBaseSchema:
    - Cross-references: pmid, doi, pmc_id
    - Core content: title, abstract, authors, affiliation_list
    - Metadata: journal, publication_year (overridden), publication_date, publication_type, language
    - Pagination: page_first, page_last
    - Metrics: citations_received, citations_made
    - Open Access: is_oa
    - Lookup tracking: lookup_method, original_id, source (overridden)
    """

    # === Primary Key (OpenAlex-specific) ===
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
        description="OpenAlex Work ID (e.g., W2148763428)",
    )
    title: Series[str] = pa.Field(
        nullable=True,
        description="Publication title when available from OpenAlex.",
    )

    # _lookup_method: inherited from PublicationBaseSchema (non-nullable, isin=LOOKUP_METHODS)

    # === Raw OpenAlex Type (replaces doc_type) ===
    publication_type: Series[str] = pa.Field(
        nullable=True,
        description="Raw OpenAlex type (article, book, dataset, etc.)",
    )
    type_crossref: Series[str] = pa.Field(
        nullable=True,
        description="Raw Crossref-compatible type exposed by OpenAlex when available.",
    )

    # Note: citations_received and citations_made inherited from base as pd.Int64Dtype

    # === Override _source to be non-nullable ===
    _source: Series[str] = pa.Field(
        nullable=False,
        eq="openalex",
        description="Data source identifier",
    )

    # === Provider-specific Fields ===
    issn: Series[str] = pa.Field(
        nullable=True,
        str_matches=ISSN_PATTERN,
        description="ISSN-L (format: NNNN-NNNN)",
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
    fwci: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Field-Weighted Citation Impact (must be non-negative)",
    )
    # Note: reference_count removed — now inherited from base as citations_made

    # === Quality Indicators ===
    is_retracted: Series[bool] = pa.Field(
        nullable=False,
        description="Whether the publication has been retracted",
    )

    # === Topics (hierarchical classification - replaces deprecated concepts) ===
    # Stored as JSON-serialized string for DataFrame compatibility
    subject_topics: Series[str] = pa.Field(
        nullable=True,
        description="Hierarchical topic classification (JSON array)",
    )

    # Primary topic (single most relevant topic for quick categorization)
    # Stored as JSON-serialized string for DataFrame compatibility
    primary_topic: Series[str] = pa.Field(
        nullable=True,
        description="Primary topic classification (JSON object)",
    )
    primary_topic_canonical_json: Series[str] = pa.Field(
        nullable=True,
        description="Canonical JSON companion for primary-topic payload.",
    )
    primary_topic_raw_json: Series[str] = pa.Field(
        nullable=True,
        description="Raw provider JSON for primary-topic payload.",
    )

    # === Grants/Funding Information ===
    # Stored as JSON-serialized string for DataFrame compatibility
    grants: Series[str] = pa.Field(
        nullable=True,
        description="Funding/grant information (JSON array)",
    )
    grants_canonical_json: Series[str] = pa.Field(
        nullable=True,
        description="Canonical JSON companion for grants payload.",
    )
    grants_raw_json: Series[str] = pa.Field(
        nullable=True,
        description="Raw provider JSON for grants payload.",
    )

    # === Classification Fields (extracted by transformer) ===
    subject_mesh: Series[str] = pa.Field(
        nullable=True,
        description="MeSH terms (JSON array of descriptor names, unified field name)",
    )

    subject_keywords: Series[str] = pa.Field(
        nullable=True,
        description="Keywords (JSON array, unified field name)",
    )

    # === External Identifier ===
    mag_id: Series[str] = pa.Field(
        nullable=True,
        description="Microsoft Academic Graph ID (legacy)",
    )

    # Note: page_first, page_last inherited from base (unified field names)
    # Note: affiliation_list inherited from base (unified field name)

    # === Author Identifiers ===
    # author_orcids: inherited from PublicationBaseSchema

    author_openalex_ids: Series[str] = pa.Field(
        nullable=True,
        description="OpenAlex author IDs as JSON array (empty string for missing)",
    )

    # === Institution Identifiers ===
    institution_ids: Series[str] = pa.Field(
        nullable=True,
        description="OpenAlex institution IDs (JSON array, e.g., I1234567890)",
    )

    institution_country_codes: Series[str] = pa.Field(
        nullable=True,
        description="ISO 2-letter country codes of affiliated institutions (JSON array)",
    )

    # === ROR Identifiers (Research Organization Registry) ===
    ror_ids: Series[str] = pa.Field(
        nullable=True,
        description="ROR IDs of affiliated institutions (JSON array, full URL format). "
        "May be empty if not returned by Works API.",
    )

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        coerce = True  # Coerce data types to match schema
