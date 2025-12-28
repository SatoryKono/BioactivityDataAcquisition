"""Pandera schema for OpenAlex Work entity.

Aligned with RULES.md v5.0 and OpenAlex API schema.
See: https://docs.openalex.org/api-entities/works
"""

from __future__ import annotations

from datetime import date

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class OpenAlexWorkSchema(ETLRecordSchema):
    """Work validation schema for Silver layer.

    Represents scientific publications from OpenAlex open index.
    """

    # === Primary Key ===
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
        description="OpenAlex Work ID (W-prefixed).",
    )

    # === Required Fields ===
    display_name: Series[str] = pa.Field(
        nullable=False,
        description="Publication title.",
    )
    type: Series[str] = pa.Field(
        nullable=False,
        isin=[
            "article",
            "book",
            "book-chapter",
            "dataset",
            "dissertation",
            "editorial",
            "erratum",
            "letter",
            "paratext",
            "peer-review",
            "reference-entry",
            "report",
            "review",
            "standard",
            "other",
        ],
        description="Work type.",
    )

    # === External Identifiers ===
    doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^10\.\d{4,}/.*$",
        description="DOI without https://doi.org/ prefix.",
    )
    pmid: Series[str] | None = pa.Field(
        nullable=True,
        description="PubMed ID.",
    )
    pmcid: Series[str] | None = pa.Field(
        nullable=True,
        description="PubMed Central ID.",
    )
    mag_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Microsoft Academic Graph ID (legacy).",
    )

    # === Publication Info ===
    publication_year: Series[int] | None = pa.Field(
        nullable=True,
        ge=1800,
        le=2030,
        description="Publication year.",
    )
    publication_date: Series[date] | None = pa.Field(
        nullable=True,
        description="Exact publication date.",
    )
    language: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^[a-z]{2}$",
        description="Language code (ISO 639-1).",
    )

    # === Primary Location (flattened) ===
    primary_location_source_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^S\d+$",
        description="OpenAlex Source ID.",
    )
    primary_location_source_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Journal/source name.",
    )
    primary_location_source_issn: Series[str] | None = pa.Field(
        nullable=True,
        description="Linking ISSN.",
    )
    primary_location_source_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["journal", "repository", "conference", "ebook platform", "book series", "other"],
        description="Source type.",
    )
    primary_location_landing_page: Series[str] | None = pa.Field(
        nullable=True,
        description="Landing page URL.",
    )
    primary_location_pdf_url: Series[str] | None = pa.Field(
        nullable=True,
        description="PDF URL.",
    )
    primary_location_version: Series[str] | None = pa.Field(
        nullable=True,
        isin=["publishedVersion", "acceptedVersion", "submittedVersion"],
        description="Version type.",
    )
    primary_location_license: Series[str] | None = pa.Field(
        nullable=True,
        description="License (cc-by, cc-by-nc, etc.).",
    )

    # === Open Access ===
    is_oa: Series[bool] | None = pa.Field(
        nullable=True,
        description="Open access availability.",
    )
    oa_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=["gold", "green", "hybrid", "bronze", "closed"],
        description="OA status category.",
    )
    oa_url: Series[str] | None = pa.Field(
        nullable=True,
        description="Open access URL.",
    )
    any_repository_has_fulltext: Series[bool] | None = pa.Field(
        nullable=True,
        description="Fulltext available in repository.",
    )

    # === Citations ===
    cited_by_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Citation count.",
    )
    cited_by_percentile_year: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=100,
        description="Citation percentile for publication year.",
    )
    referenced_works_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of references.",
    )

    # === Bibliographic Info ===
    biblio_volume: Series[str] | None = pa.Field(
        nullable=True,
        description="Volume.",
    )
    biblio_issue: Series[str] | None = pa.Field(
        nullable=True,
        description="Issue.",
    )
    biblio_first_page: Series[str] | None = pa.Field(
        nullable=True,
        description="First page.",
    )
    biblio_last_page: Series[str] | None = pa.Field(
        nullable=True,
        description="Last page.",
    )

    # === Flags ===
    is_retracted: Series[bool] | None = pa.Field(
        nullable=True,
        description="Publication retracted.",
    )
    is_paratext: Series[bool] | None = pa.Field(
        nullable=True,
        description="Is paratext (editorial, erratum, etc.).",
    )
    has_fulltext: Series[bool] | None = pa.Field(
        nullable=True,
        description="Fulltext available in OpenAlex.",
    )
    fulltext_origin: Series[str] | None = pa.Field(
        nullable=True,
        description="Fulltext source.",
    )

    # === Abstract ===
    abstract_inverted_index: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON inverted index of abstract.",
    )

    # === Primary Topic (flattened) ===
    primary_topic_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^T\d+$",
        description="Primary topic ID.",
    )
    primary_topic_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Topic name.",
    )
    primary_topic_score: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=1,
        description="Topic relevance score.",
    )
    primary_topic_subfield: Series[str] | None = pa.Field(
        nullable=True,
        description="Subfield name.",
    )
    primary_topic_field: Series[str] | None = pa.Field(
        nullable=True,
        description="Field name.",
    )
    primary_topic_domain: Series[str] | None = pa.Field(
        nullable=True,
        description="Domain name.",
    )

    # === Aggregated Fields ===
    keywords: Series[str] | None = pa.Field(
        nullable=True,
        description="Keywords joined by '; '.",
    )
    sustainable_development_goals: Series[str] | None = pa.Field(
        nullable=True,
        description="SDGs joined by '; ' (id:name:score format).",
    )
    grants: Series[str] | None = pa.Field(
        nullable=True,
        description="Grants joined by '; ' (funder_id:award_id format).",
    )
    indexed_in: Series[str] | None = pa.Field(
        nullable=True,
        description="Indexes joined by '; ' (crossref, pubmed, doaj, etc.).",
    )
    related_works: Series[str] | None = pa.Field(
        nullable=True,
        description="Related work IDs joined by '; '.",
    )

    # === Metrics ===
    fwci: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Field-Weighted Citation Impact.",
    )
    countries_distinct_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of distinct author countries.",
    )
    institutions_distinct_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of distinct institutions.",
    )

    # === Corresponding Authors ===
    corresponding_author_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Corresponding author OpenAlex IDs joined by '; '.",
    )
    corresponding_institution_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Corresponding institution IDs joined by '; '.",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Silver layer allows extra columns
        ordered = True
        coerce = True
