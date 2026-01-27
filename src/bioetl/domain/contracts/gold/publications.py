"""Publication Gold layer data contracts.

Contains Pandera DataFrameModel schemas for cross-provider publication entities
in the Gold layer:
- PubMed: Publication metadata with MEDLINE-specific fields
- CrossRef: Publication metadata via DOI resolution
- OpenAlex: Publication metadata from OpenAlex Works API
- SemanticScholar: Publication metadata with citation metrics

All schemas inherit from PublicationGoldBaseSchema which provides:
- Unified cross-reference IDs (doi, pmid, pmc_id)
- Unified year range (1450-2150)
- Unified nullable policy (doc_type always nullable)
- Common metadata and lineage fields

Int->Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md Section 2.6.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold.publication_base import PublicationGoldBaseSchema


class PubMedPublicationGoldSchema(PublicationGoldBaseSchema):
    """Schema for PubMed Publication in Gold layer.

    Inherits common fields from PublicationGoldBaseSchema and adds
    PubMed-specific fields for forensic retention and detailed analysis.

    See: https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_230101.dtd
    """

    # Primary key override (pmid is non-nullable for PubMed)
    pmid: Series[str] = pa.Field(nullable=False)

    # === PubMed-specific content ===
    abstract: Series[str] = pa.Field(nullable=True)
    abstract_structured: Series[bool] = pa.Field(
        nullable=True
    )  # Whether abstract has NLM sections
    vernacular_title: Series[str] = pa.Field(
        nullable=True
    )  # Original non-English title

    # === Journal information (PubMed-specific) ===
    journal_abbrev: Series[str] = pa.Field(nullable=True)
    journal_title: Series[str] = pa.Field(nullable=True)  # Full journal name (PubMed)
    journal_iso_abbrev: Series[str] = pa.Field(nullable=True)  # ISO abbreviation
    journal_issn_type: Series[str] = pa.Field(
        nullable=True
    )  # ISSN type: Print/Electronic/Linking
    issn: Series[str] = pa.Field(nullable=True)
    nlm_unique_id: Series[str] = pa.Field(nullable=True)  # NLM catalog ID
    issue: Series[str] = pa.Field(nullable=True)

    # === Page information (PubMed-specific legacy fields) ===
    pages: Series[str] = pa.Field(nullable=True)  # Legacy: medline_pgn format
    medline_pgn: Series[str] = pa.Field(nullable=True)  # Original PubMed pagination

    # === Date fields (PubMed-specific) ===
    pub_date: Series[str] = pa.Field(nullable=True)
    pub_month: Series[float] = pa.Field(nullable=True, coerce=True)  # Month (1-12)
    pub_day: Series[float] = pa.Field(nullable=True, coerce=True)  # Day (1-31)
    publication_year: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Legacy alias
    accepted_date: Series[str] = pa.Field(nullable=True)
    received_date: Series[str] = pa.Field(nullable=True)
    revised_date: Series[str] = pa.Field(nullable=True)
    epub_date: Series[str] = pa.Field(nullable=True)
    # MEDLINE-specific dates
    date_completed: Series[str] = pa.Field(
        nullable=True
    )  # MEDLINE processing completion
    date_revised: Series[str] = pa.Field(
        nullable=True
    )  # Record revision date (MEDLINE)

    # === Publication status and types ===
    publication_status: Series[str] = pa.Field(
        nullable=True
    )  # ppublish/epublish/aheadofprint
    publication_type_list: Series[str] = pa.Field(
        nullable=True
    )  # JSON array of pub types
    publication_types: Series[object] = pa.Field(nullable=True)  # list[str]

    # === Classification (PubMed-specific) ===
    keywords: Series[object] = pa.Field(nullable=True)  # list[str]
    mesh_terms: Series[object] = pa.Field(nullable=True)  # list[str]
    chemicals: Series[object] = pa.Field(nullable=True)  # list[str]
    databanks: Series[object] = pa.Field(nullable=True)  # list[str]
    gene_symbols: Series[object] = pa.Field(nullable=True)  # list[str]
    citation_subset: Series[str] = pa.Field(
        nullable=True
    )  # Citation subset codes (e.g., 'AIM')
    country: Series[str] = pa.Field(nullable=True)

    # === Counts (denormalized for query efficiency) ===
    author_count: Series[float] = pa.Field(nullable=True, coerce=True)
    mesh_heading_count: Series[float] = pa.Field(nullable=True, coerce=True)
    keyword_count: Series[float] = pa.Field(nullable=True, coerce=True)
    grant_count: Series[float] = pa.Field(nullable=True, coerce=True)
    chemical_count: Series[float] = pa.Field(nullable=True, coerce=True)

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class CrossRefPublicationGoldSchema(PublicationGoldBaseSchema):
    """Schema for CrossRef Publication in Gold layer.

    Inherits common fields from PublicationGoldBaseSchema and adds
    CrossRef-specific fields for DOI-based metadata enrichment.
    """

    # Primary key override (doi is non-nullable for CrossRef)
    doi: Series[str] = pa.Field(nullable=False)

    # === CrossRef-specific fields ===
    issn: Series[object] = pa.Field(nullable=True)  # list[str]
    publisher: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)

    # === Date fields (CrossRef-specific) ===
    published_print: Series[str] = pa.Field(nullable=True)  # Legacy: provider-specific
    published_online: Series[str] = pa.Field(nullable=True)  # Legacy: provider-specific
    published: Series[str] = pa.Field(nullable=True)  # Canonical publication date

    # === Metadata (CrossRef-specific) ===
    license_url: Series[str] = pa.Field(nullable=True)
    subjects: Series[object] = pa.Field(nullable=True)  # list[str]

    # === Content domain (Crossmark/license restrictions) ===
    content_domain_domains: Series[object] = pa.Field(nullable=True)  # list[str]
    content_domain_crossmark_restriction: Series[bool] = pa.Field(
        nullable=True, coerce=True
    )

    # === Alternative identifiers (publisher-specific IDs, e.g., PII) ===
    alternative_id: Series[object] = pa.Field(nullable=True)  # list[str]

    # === Short container title ===
    short_container_title: Series[object] = pa.Field(nullable=True)  # list[str]

    # === ISSN by type ===
    issn_print: Series[str] = pa.Field(nullable=True)
    issn_electronic: Series[str] = pa.Field(nullable=True)

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class OpenAlexPublicationGoldSchema(PublicationGoldBaseSchema):
    """Schema for OpenAlex Publication in Gold layer.

    Inherits common fields from PublicationGoldBaseSchema and adds
    OpenAlex-specific fields for batch DOI resolution with title fallback.
    """

    # Primary key (OpenAlex-specific)
    openalex_id: Series[str] = pa.Field(nullable=False)

    # === OpenAlex-specific content ===
    abstract: Series[str] = pa.Field(nullable=True)
    affiliations: Series[object] = pa.Field(nullable=True)  # list[str]
    concepts: Series[object] = pa.Field(nullable=True)  # list[str]
    mesh: Series[object] = pa.Field(nullable=True)  # list[str] - MeSH terms
    keywords: Series[object] = pa.Field(nullable=True)  # list[str]
    mag_id: Series[str] = pa.Field(nullable=True)  # Microsoft Academic Graph ID

    # === Journal info (OpenAlex-specific) ===
    issn: Series[str] = pa.Field(nullable=True)
    publisher: Series[str] = pa.Field(nullable=True)

    # === Open Access (OpenAlex-specific) ===
    is_oa: Series[bool] = pa.Field(nullable=True, coerce=True)
    oa_status: Series[str] = pa.Field(nullable=True)

    # Override lookup_method to be non-nullable (OpenAlex always provides this)
    lookup_method: Series[str] = pa.Field(nullable=False, alias="_lookup_method")

    # Override source to be non-nullable (always "openalex")
    source: Series[str] = pa.Field(nullable=False, alias="_source")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class SemanticScholarPublicationGoldSchema(PublicationGoldBaseSchema):
    """Schema for Semantic Scholar Publication in Gold layer.

    Inherits common fields from PublicationGoldBaseSchema and adds
    Semantic Scholar-specific fields for citation metrics and AI-generated content.
    """

    # Primary key (S2-specific)
    paper_id: Series[str] = pa.Field(nullable=False)

    # === S2-specific identifiers ===
    arxiv_id: Series[str] = pa.Field(nullable=True)
    corpus_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64

    # === S2-specific content ===
    abstract: Series[str] = pa.Field(nullable=True)  # Now included per unified schema
    tldr: Series[str] = pa.Field(nullable=True)  # AI-generated summary

    # === Page information (S2-specific legacy) ===
    pages: Series[str] = pa.Field(nullable=True)  # Legacy: "first-last" format

    # === Journal/Venue (S2-specific) ===
    venue: Series[str] = pa.Field(nullable=True)

    # === Open Access (S2-specific) ===
    is_oa: Series[bool] = pa.Field(nullable=True, coerce=True)
    open_access_url: Series[str] = pa.Field(nullable=True)
    oa_status: Series[str] = pa.Field(nullable=True)

    # === Classification (JSON strings) ===
    fields_of_study: Series[str] = pa.Field(nullable=True)
    publication_types: Series[str] = pa.Field(nullable=True)

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


__all__ = [
    "CrossRefPublicationGoldSchema",
    "OpenAlexPublicationGoldSchema",
    "PubMedPublicationGoldSchema",
    "SemanticScholarPublicationGoldSchema",
]
