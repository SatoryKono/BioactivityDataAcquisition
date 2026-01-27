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

from bioetl.domain.contracts.gold.publication_base import PublicationGoldBaseSchema


class PubMedPublicationGoldSchema(PublicationGoldBaseSchema):
    """Schema for PubMed Publication in Gold layer.

    Includes PubMed-specific fields for forensic retention and detailed analysis.
    See: https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_230101.dtd
    """

    # === Primary Key Override ===
    pmid: Series[str] = pa.Field(nullable=False)

    # === PubMed-Specific Fields ===
    abstract_structured: Series[bool] = pa.Field(
        nullable=True
    )  # Whether abstract has NLM sections
    vernacular_title: Series[str] = pa.Field(
        nullable=True
    )  # Original non-English title

    # Journal information
    journal_abbrev: Series[str] = pa.Field(nullable=True)
    journal_title: Series[str] = pa.Field(nullable=True)  # Full journal name (PubMed)
    journal_iso_abbrev: Series[str] = pa.Field(nullable=True)  # ISO abbreviation
    journal_issn_type: Series[str] = pa.Field(
        nullable=True
    )  # ISSN type: Print/Electronic/Linking
    issn: Series[str] = pa.Field(nullable=True)
    nlm_unique_id: Series[str] = pa.Field(nullable=True)  # NLM catalog ID

    # Page information
    pages: Series[str] = pa.Field(nullable=True)  # Legacy: medline_pgn format
    medline_pgn: Series[str] = pa.Field(nullable=True)  # Original PubMed pagination

    # Date fields
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
    mesh_terms: Series[object] = pa.Field(nullable=True)  # list[str]
    chemicals: Series[object] = pa.Field(nullable=True)  # list[str]
    databanks: Series[object] = pa.Field(nullable=True)  # list[str]
    gene_symbols: Series[object] = pa.Field(nullable=True)  # list[str]
    citation_subset: Series[str] = pa.Field(
        nullable=True
    )  # Citation subset codes (e.g., 'AIM')
    country: Series[str] = pa.Field(nullable=True)

    # Counts
    author_count: Series[float] = pa.Field(nullable=True, coerce=True)
    mesh_heading_count: Series[float] = pa.Field(nullable=True, coerce=True)
    keyword_count: Series[float] = pa.Field(nullable=True, coerce=True)
    grant_count: Series[float] = pa.Field(nullable=True, coerce=True)
    chemical_count: Series[float] = pa.Field(nullable=True, coerce=True)


class CrossRefPublicationGoldSchema(PublicationGoldBaseSchema):
    """Schema for CrossRef Publication in Gold layer.

    Used for enriching publication records with CrossRef metadata via DOI resolution.
    """

    # === Primary Key Override ===
    doi: Series[str] = pa.Field(nullable=False)

    # === CrossRef-Specific Fields ===
    issn: Series[object] = pa.Field(nullable=True)  # list[str]
    publisher: Series[str] = pa.Field(nullable=True)

    published_print: Series[str] = pa.Field(nullable=True)  # Legacy: provider-specific
    published_online: Series[str] = pa.Field(nullable=True)  # Legacy: provider-specific

    license_url: Series[str] = pa.Field(nullable=True)
    subjects: Series[object] = pa.Field(nullable=True)  # list[str]

    content_domain_domains: Series[object] = pa.Field(nullable=True)  # list[str]
    content_domain_crossmark_restriction: Series[bool] = pa.Field(
        nullable=True, coerce=True
    )

    alternative_id: Series[object] = pa.Field(nullable=True)  # list[str]

    published: Series[str] = pa.Field(nullable=True)

    short_container_title: Series[object] = pa.Field(nullable=True)  # list[str]

    issn_print: Series[str] = pa.Field(nullable=True)
    issn_electronic: Series[str] = pa.Field(nullable=True)


class OpenAlexPublicationGoldSchema(PublicationGoldBaseSchema):
    """Schema for OpenAlex Publication in Gold layer.

    Used for batch DOI resolution with title fallback via OpenAlex Works API.
    """

    # === Primary Key ===
    openalex_id: Series[str] = pa.Field(nullable=False)

    # === System Fields Override ===
    source: Series[str] = pa.Field(nullable=False, alias="_source")
    lookup_method: Series[str] = pa.Field(nullable=False, alias="_lookup_method")

    # === OpenAlex-Specific Fields ===
    affiliations: Series[object] = pa.Field(nullable=True)  # list[str]
    concepts: Series[object] = pa.Field(nullable=True)  # list[str]
    mesh: Series[object] = pa.Field(nullable=True)  # list[str] - MeSH terms
    mag_id: Series[str] = pa.Field(nullable=True)

    issn: Series[str] = pa.Field(nullable=True)
    publisher: Series[str] = pa.Field(nullable=True)

    # New metrics/status fields (Phase 2 & 5)
    fwci: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    is_retracted: Series[bool] = pa.Field(nullable=True, coerce=True)
    primary_topic: Series[object] = pa.Field(nullable=True)
    topics: Series[object] = pa.Field(nullable=True)
    grants: Series[object] = pa.Field(nullable=True)


class SemanticScholarPublicationGoldSchema(PublicationGoldBaseSchema):
    """Schema for Semantic Scholar Publication in Gold layer.

    Used for enriching publication records with Semantic Scholar metadata.
    """

    # === Primary Key ===
    paper_id: Series[str] = pa.Field(nullable=False)

    # === Semantic Scholar Specific Fields ===
    arxiv_id: Series[str] = pa.Field(nullable=True)
    corpus_id: Series[float] = pa.Field(nullable=True, coerce=True)

    tldr: Series[str] = pa.Field(nullable=True)

    pages: Series[str] = pa.Field(nullable=True)  # Legacy: "first-last" format
    venue: Series[str] = pa.Field(nullable=True)

    open_access_url: Series[str] = pa.Field(nullable=True)

    # Updated to object (list) for unification
    fields_of_study: Series[object] = pa.Field(nullable=True)
    publication_types: Series[object] = pa.Field(nullable=True)


__all__ = [
    "CrossRefPublicationGoldSchema",
    "OpenAlexPublicationGoldSchema",
    "PubMedPublicationGoldSchema",
    "SemanticScholarPublicationGoldSchema",
]
