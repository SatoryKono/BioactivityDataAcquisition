"""Pandera schema for OpenAlex Institution entity.

Aligned with RULES.md v5.0 and OpenAlex API schema.
See: https://docs.openalex.org/api-entities/institutions
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class OpenAlexInstitutionSchema(ETLRecordSchema):
    """Institution validation schema for Silver layer.

    Represents universities, companies, and research organizations.
    """

    # === Primary Key ===
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^I\d+$",
        description="OpenAlex Institution ID (I-prefixed).",
    )

    # === Required Fields ===
    display_name: Series[str] = pa.Field(
        nullable=False,
        description="Institution name.",
    )

    # === External Identifiers ===
    ror: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^0[a-z0-9]{8}$",
        description="ROR ID without URL prefix.",
    )

    # === Classification ===
    country_code: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^[A-Z]{2}$",
        description="Country code (ISO 3166-1 alpha-2).",
    )
    type: Series[str] | None = pa.Field(
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

    # === Web ===
    homepage_url: Series[str] | None = pa.Field(
        nullable=True,
        description="Website URL.",
    )
    image_url: Series[str] | None = pa.Field(
        nullable=True,
        description="Logo/image URL.",
    )
    image_thumbnail_url: Series[str] | None = pa.Field(
        nullable=True,
        description="Thumbnail URL.",
    )

    # === Name Variants ===
    display_name_acronyms: Series[str] | None = pa.Field(
        nullable=True,
        description="Acronyms joined by '; '.",
    )
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
        description="Total citations.",
    )

    # === Geo (flattened) ===
    geo_city: Series[str] | None = pa.Field(
        nullable=True,
        description="City.",
    )
    geo_region: Series[str] | None = pa.Field(
        nullable=True,
        description="Region/state.",
    )
    geo_country: Series[str] | None = pa.Field(
        nullable=True,
        description="Country full name.",
    )
    geo_latitude: Series[float] | None = pa.Field(
        nullable=True,
        ge=-90,
        le=90,
        description="Latitude.",
    )
    geo_longitude: Series[float] | None = pa.Field(
        nullable=True,
        ge=-180,
        le=180,
        description="Longitude.",
    )
    geo_geonames_city_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Geonames city ID.",
    )

    # === Relationships ===
    associated_institutions: Series[str] | None = pa.Field(
        nullable=True,
        description="Associated institutions as JSON.",
    )
    lineage: Series[str] | None = pa.Field(
        nullable=True,
        description="Parent institution IDs joined by '; '.",
    )
    repositories: Series[str] | None = pa.Field(
        nullable=True,
        description="Repository IDs joined by '; '.",
    )

    class Config:
        """Pandera configuration."""

        strict = False
        ordered = True
        coerce = True
