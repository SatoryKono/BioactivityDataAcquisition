"""Pandera schema for OpenAlex Author entity.

Aligned with RULES.md v5.0 and OpenAlex API schema.
See: https://docs.openalex.org/api-entities/authors
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class OpenAlexAuthorSchema(ETLRecordSchema):
    """Author validation schema for Silver layer.

    Represents author profiles from OpenAlex with metrics and affiliations.
    """

    # === Primary Key ===
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^A\d+$",
        description="OpenAlex Author ID (A-prefixed).",
    )

    # === Required Fields ===
    display_name: Series[str] = pa.Field(
        nullable=False,
        description="Display name.",
    )

    # === External Identifiers ===
    orcid: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$",
        description="ORCID without URL prefix.",
    )
    scopus_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Scopus Author ID.",
    )

    # === Name Variants ===
    display_name_alternatives: Series[str] | None = pa.Field(
        nullable=True,
        description="Alternative names joined by '; '.",
    )

    # === Metrics ===
    works_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of works.",
    )
    cited_by_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Total citation count.",
    )
    h_index: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="h-index.",
    )
    i10_index: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="i10-index (works with 10+ citations).",
    )
    two_year_mean_citedness: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Mean citedness over 2 years.",
    )

    # === Last Known Institution (flattened) ===
    last_known_institution_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^I\d+$",
        description="Last known institution OpenAlex ID.",
    )
    last_known_institution_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Institution name.",
    )
    last_known_institution_ror: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^0[a-z0-9]{8}$",
        description="ROR ID without URL prefix.",
    )
    last_known_institution_country: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^[A-Z]{2}$",
        description="Country code (ISO 3166-1 alpha-2).",
    )
    last_known_institution_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "education",
            "company",
            "healthcare",
            "government",
            "nonprofit",
            "facility",
            "archive",
            "other",
        ],
        description="Institution type.",
    )
    last_known_institution_lineage: Series[str] | None = pa.Field(
        nullable=True,
        description="Lineage institution IDs joined by '; '.",
    )

    # === Aggregated Fields ===
    affiliations_history: Series[str] | None = pa.Field(
        nullable=True,
        description="Affiliation history as JSON (institution_id:years).",
    )
    topics: Series[str] | None = pa.Field(
        nullable=True,
        description="Top topics joined by '; ' (id:name:count format).",
    )

    class Config:
        """Pandera configuration."""

        strict = False
        ordered = True
        coerce = True
