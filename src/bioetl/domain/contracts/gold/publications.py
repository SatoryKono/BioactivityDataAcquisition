"""Publication Gold layer data contracts.

Contains Pandera DataFrameModel schemas for cross-provider publication entities
in the Gold layer:
- PubMed: Publication metadata with MEDLINE-specific fields
- CrossRef: Publication metadata via DOI resolution
- OpenAlex: Publication metadata from OpenAlex Works API
- SemanticScholar: Publication metadata with citation metrics

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class PubMedPublicationGoldSchema(pa.DataFrameModel):
    """Schema for PubMed Publication in Gold layer.

    Includes PubMed-specific fields for forensic retention and detailed analysis.
    See: https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_230101.dtd
    """

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    pmid: Series[str] = pa.Field(nullable=False)
    doi: Series[str] = pa.Field(nullable=True)
    pmc_id: Series[str] = pa.Field(nullable=True)
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    abstract_structured: Series[bool] = pa.Field(
        nullable=True
    )  # Whether abstract has NLM sections
    # Note: vernacular_title excluded from transformer output per design

    # Journal information
    journal: Series[str] = pa.Field(nullable=True)
    journal_abbrev: Series[str] = pa.Field(nullable=True)
    # PubMed-specific journal fields (forensic retention)
    journal_full_title: Series[str] = pa.Field(
        nullable=True
    )  # Full journal name (PubMed only, will be removed after PubMed unification)
    journal_iso_abbrev: Series[str] = pa.Field(nullable=True)  # ISO abbreviation
    journal_issn_type: Series[str] = pa.Field(
        nullable=True
    )  # ISSN type: Print/Electronic/Linking
    issn: Series[str] = pa.Field(nullable=True)
    nlm_unique_id: Series[str] = pa.Field(nullable=True)  # NLM catalog ID
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)

    # Page information
    pages: Series[str] = pa.Field(nullable=True)  # Legacy: medline_pgn format
    medline_pgn: Series[str] = pa.Field(nullable=True)  # Original PubMed pagination
    first_page: Series[str] = pa.Field(nullable=True)  # Unified: parsed from pages
    last_page: Series[str] = pa.Field(nullable=True)  # Unified: parsed from pages

    # Authors and affiliations
    authors: Series[str] = pa.Field(nullable=True)  # JSON-serialized list
    affiliations: Series[str] = pa.Field(
        nullable=True
    )  # JSON array of unique affiliations
    authors_with_affiliations: Series[str] = pa.Field(
        nullable=True
    )  # JSON array: author -> affiliations
    structured_affiliations: Series[str] = pa.Field(
        nullable=True
    )  # JSON array with ROR/GRID identifiers

    # Date fields
    pub_month: Series[float] = pa.Field(nullable=True, coerce=True)  # Month (1-12)
    pub_day: Series[float] = pa.Field(nullable=True, coerce=True)  # Day (1-31)
    publication_date: Series[str] = pa.Field(nullable=True)  # Unified: YYYY-MM-DD
    year: Series[float] = pa.Field(nullable=True, coerce=True)
    # Note: accepted_date, received_date, revised_date, epub_date excluded per design
    # MEDLINE-specific dates
    date_completed: Series[str] = pa.Field(
        nullable=True
    )  # MEDLINE processing completion
    date_revised: Series[str] = pa.Field(
        nullable=True
    )  # Record revision date (MEDLINE)

    # Publication status and types
    publication_status: Series[str] = pa.Field(
        nullable=True
    )  # ppublish/epublish/aheadofprint
    publication_type_list: Series[str] = pa.Field(
        nullable=True
    )  # JSON array of pub types
    publication_types: Series[object] = pa.Field(nullable=True)  # list[str]

    # Classification
    keywords: Series[object] = pa.Field(nullable=True)  # list[str]
    mesh_terms: Series[object] = pa.Field(nullable=True)  # list[str]
    chemicals: Series[object] = pa.Field(nullable=True)  # list[str]
    databanks: Series[object] = pa.Field(nullable=True)  # list[str]
    gene_symbols: Series[object] = pa.Field(nullable=True)  # list[str]
    citation_subset: Series[str] = pa.Field(
        nullable=True
    )  # Citation subset codes (e.g., 'AIM')
    language: Series[str] = pa.Field(nullable=True)
    country: Series[str] = pa.Field(nullable=True)

    # Counts (denormalized for query efficiency)
    author_count: Series[float] = pa.Field(nullable=True, coerce=True)
    mesh_heading_count: Series[float] = pa.Field(nullable=True, coerce=True)
    keyword_count: Series[float] = pa.Field(nullable=True, coerce=True)
    grant_count: Series[float] = pa.Field(nullable=True, coerce=True)
    reference_count: Series[float] = pa.Field(nullable=True, coerce=True)
    chemical_count: Series[float] = pa.Field(nullable=True, coerce=True)

    # Source tracking (maps to _source column in DataFrame)
    source: Series[str] = pa.Field(nullable=True, alias="_source")

    # Lookup metadata
    # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    # _original_id: Original identifier used for lookup
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class CrossRefPublicationGoldSchema(pa.DataFrameModel):
    """Schema for CrossRef Publication in Gold layer.

    Used for enriching publication records with CrossRef metadata via DOI resolution.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    # doi: Digital Object Identifier (lowercase, without "https://doi.org/") - Primary key
    doi: Series[str] = pa.Field(nullable=False)

    # Note: pmid and pmc_id excluded - CrossRef API doesn't provide PubMed identifiers
    # and transformer explicitly removes these fields from output

    # Core fields
    title: Series[str] = pa.Field(nullable=True)
    authors: Series[str] = pa.Field(nullable=True)  # JSON-serialized list
    journal: Series[str] = pa.Field(nullable=True)
    issn: Series[object] = pa.Field(nullable=True)  # list[str]
    publisher: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    first_page: Series[str] = pa.Field(nullable=True)
    last_page: Series[str] = pa.Field(nullable=True)

    # Date fields
    year: Series[float] = pa.Field(nullable=True, ge=1900, le=2100, coerce=True)
    publication_date: Series[str] = pa.Field(nullable=True)  # Unified: YYYY-MM-DD
    published_print: Series[str] = pa.Field(nullable=True)  # Legacy: provider-specific
    published_online: Series[str] = pa.Field(nullable=True)  # Legacy: provider-specific

    # Metadata
    # Note: doc_type excluded; CrossRef uses raw 'type' field instead
    type: Series[str] = pa.Field(
        nullable=True
    )  # Raw CrossRef type (journal-article, etc.)
    citation_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    reference_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    language: Series[str] = pa.Field(nullable=True)
    license_url: Series[str] = pa.Field(nullable=True)
    subjects: Series[object] = pa.Field(nullable=True)  # list[str]

    # Content domain (Crossmark/license restrictions)
    content_domain_domains: Series[object] = pa.Field(nullable=True)  # list[str]
    content_domain_crossmark_restriction: Series[bool] = pa.Field(
        nullable=True, coerce=True
    )

    # Alternative identifiers (publisher-specific IDs, e.g., PII)
    alternative_id: Series[object] = pa.Field(nullable=True)  # list[str]

    # Canonical publication date
    published: Series[str] = pa.Field(nullable=True)

    # Short container title
    short_container_title: Series[object] = pa.Field(nullable=True)  # list[str]

    # ISSN by type
    issn_print: Series[str] = pa.Field(nullable=True)
    issn_electronic: Series[str] = pa.Field(nullable=True)

    # Source tracking (maps to _source column in DataFrame)
    source: Series[str] = pa.Field(nullable=True, alias="_source")

    # Lookup metadata
    # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    # _original_id: Original identifier used for lookup
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class OpenAlexPublicationGoldSchema(pa.DataFrameModel):
    """Schema for OpenAlex Publication in Gold layer.

    Used for batch DOI resolution with title fallback via OpenAlex Works API.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key
    openalex_id: Series[str] = pa.Field(nullable=False)

    # Cross-reference IDs for linking publications across providers
    # doi: Digital Object Identifier (lowercase, without "https://doi.org/")
    doi: Series[str] = pa.Field(nullable=True)
    # pmid: PubMed ID (numeric string: "12345678")
    pmid: Series[str] = pa.Field(nullable=True)
    # Note: pmc_id excluded from transformer output per design
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    authors: Series[str] = pa.Field(nullable=True)  # JSON-serialized list
    affiliations: Series[object] = pa.Field(nullable=True)  # list[str]
    # NOTE: concepts field removed - OpenAlex deprecated concepts in 2024, use topics instead
    mesh_terms: Series[object] = pa.Field(nullable=True)  # list[str] - MeSH terms
    keywords: Series[object] = pa.Field(nullable=True)  # list[str]
    mag_id: Series[str] = pa.Field(nullable=True)  # Microsoft Academic Graph ID

    # Journal info
    journal: Series[str] = pa.Field(nullable=True)
    issn: Series[str] = pa.Field(nullable=True)
    publisher: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)

    # Page fields (from biblio object)
    first_page: Series[str] = pa.Field(nullable=True)
    last_page: Series[str] = pa.Field(nullable=True)

    # Date fields
    year: Series[float] = pa.Field(nullable=True, ge=1500, le=2100, coerce=True)
    publication_date: Series[str] = pa.Field(nullable=True)

    # Metadata
    # Note: doc_type excluded; OpenAlex uses raw 'type' field instead
    type: Series[str] = pa.Field(nullable=True)  # Raw OpenAlex type (article, etc.)
    is_oa: Series[bool] = pa.Field(nullable=True, coerce=True)
    oa_status: Series[str] = pa.Field(nullable=True)
    is_retracted: Series[bool] = pa.Field(
        nullable=True, coerce=True
    )  # Quality indicator
    # OpenAlex source field: cited_by_count
    # Unified BioETL field: citation_count (standardized across all providers)
    citation_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    language: Series[str] = pa.Field(nullable=True)

    # Metrics
    fwci: Series[float] = pa.Field(
        nullable=True, ge=0
    )  # Field-Weighted Citation Impact
    reference_count: Series[float] = pa.Field(
        nullable=True, ge=0, coerce=True
    )  # Number of references

    # Topics (hierarchical 4-level classification - replaces deprecated concepts)
    topics: Series[str] = pa.Field(nullable=True)  # JSON array
    primary_topic: Series[str] = pa.Field(nullable=True)  # JSON object

    # Grants/funding information
    grants: Series[str] = pa.Field(nullable=True)  # JSON array

    # Institution identifiers
    institution_ids: Series[object] = pa.Field(nullable=True)  # list[str]
    institution_country_codes: Series[object] = pa.Field(nullable=True)  # list[str]
    ror_ids: Series[str] = pa.Field(nullable=True)  # JSON array of ROR URLs

    # Author identifiers
    author_ids: Series[str] = pa.Field(nullable=True)  # OpenAlex author IDs
    author_orcids: Series[str] = pa.Field(nullable=True)  # ORCID IDs

    # Source tracking (maps to _source column in DataFrame)
    source: Series[str] = pa.Field(nullable=False, alias="_source")

    # Lookup metadata
    # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    # _original_id: Original identifier used for lookup
    lookup_method: Series[str] = pa.Field(nullable=False, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class SemanticScholarPublicationGoldSchema(pa.DataFrameModel):
    """Schema for Semantic Scholar Publication in Gold layer.

    Used for enriching publication records with Semantic Scholar metadata.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key
    paper_id: Series[str] = pa.Field(nullable=False)

    # External IDs
    doi: Series[str] = pa.Field(nullable=True)
    pmid: Series[str] = pa.Field(nullable=True)
    # Note: pmc_id and arxiv_id excluded from transformer output per design
    corpus_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64

    # Core fields
    title: Series[str] = pa.Field(nullable=True)
    # abstract excluded per user request
    tldr: Series[str] = pa.Field(nullable=True)
    year: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    publication_date: Series[str] = pa.Field(nullable=True)

    # Journal/Venue
    journal: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)  # Parsed from combined volume/issue
    pages: Series[str] = pa.Field(nullable=True)  # Legacy: "first-last" format
    first_page: Series[str] = pa.Field(nullable=True)  # Unified: parsed from pages
    last_page: Series[str] = pa.Field(nullable=True)  # Unified: parsed from pages
    venue: Series[str] = pa.Field(nullable=True)

    # Metrics
    citation_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)  # int64
    reference_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)  # int64
    influential_citation_count: Series[float] = pa.Field(
        nullable=True, ge=0, coerce=True
    )  # int64

    # Open Access
    is_oa: Series[bool] = pa.Field(nullable=True, coerce=True)
    open_access_url: Series[str] = pa.Field(nullable=True)
    oa_status: Series[str] = pa.Field(nullable=True)

    # Classification (JSON strings)
    fields_of_study: Series[str] = pa.Field(nullable=True)
    publication_types: Series[str] = pa.Field(nullable=True)
    citation_contexts: Series[str] = pa.Field(nullable=True)  # JSON array

    # Author affiliations
    affiliations: Series[str] = pa.Field(nullable=True)  # JSON array

    # Author identifiers
    author_ids: Series[str] = pa.Field(nullable=True)  # JSON array of S2 author IDs
    author_s2_ids: Series[str] = pa.Field(nullable=True)  # JSON array (40-char hex)
    author_orcids: Series[str] = pa.Field(nullable=True)  # JSON array of ORCIDs
    author_h_indices: Series[str] = pa.Field(
        nullable=True
    )  # JSON array of h-index values

    # External identifiers
    dblp_id: Series[str] = pa.Field(nullable=True)  # DBLP publication key

    # Source tracking (maps to _source column in DataFrame)
    source: Series[str] = pa.Field(nullable=True, alias="_source")

    # Lookup metadata
    # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    # _original_id: Original identifier used for lookup
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


__all__ = [
    "CrossRefPublicationGoldSchema",
    "OpenAlexPublicationGoldSchema",
    "PubMedPublicationGoldSchema",
    "SemanticScholarPublicationGoldSchema",
]
