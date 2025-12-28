"""Pandera schema for OpenAlex Source entity.

Aligned with RULES.md v5.0 and OpenAlex API schema.
See: https://docs.openalex.org/api-entities/sources
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class OpenAlexSourceSchema(ETLRecordSchema):
    """Source validation schema for Silver layer.

    Represents journals, repositories, conferences, and ebook platforms.
    """

    # === Primary Key ===
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^S\d+$",
        description="OpenAlex Source ID (S-prefixed).",
    )

    # === Required Fields ===
    display_name: Series[str] = pa.Field(
        nullable=False,
        description="Source name.",
    )

    # === Identifiers ===
    issn_l: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{3}[\dX]$",
        description="Linking ISSN.",
    )
    issn: Series[str] | None = pa.Field(
        nullable=True,
        description="All ISSNs joined by '; '.",
    )

    # === Classification ===
    type: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "journal",
            "repository",
            "conference",
            "ebook platform",
            "book series",
            "other",
        ],
        description="Source type.",
    )

    # === Host Organization (flattened) ===
    host_organization_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^P\d+$",
        description="Publisher OpenAlex ID.",
    )
    host_organization_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Publisher name.",
    )
    host_organization_lineage: Series[str] | None = pa.Field(
        nullable=True,
        description="Publisher lineage IDs joined by '; '.",
    )

    # === Web ===
    homepage_url: Series[str] | None = pa.Field(
        nullable=True,
        description="Homepage URL.",
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
    summary_stats_h_index: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Source h-index.",
    )
    summary_stats_2yr_mean_citedness: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        description="2-year mean citedness (Impact Factor proxy).",
    )

    # === Open Access ===
    is_oa: Series[bool] | None = pa.Field(
        nullable=True,
        description="Fully open access source.",
    )
    is_in_doaj: Series[bool] | None = pa.Field(
        nullable=True,
        description="Listed in DOAJ.",
    )
    apc_usd: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="APC in USD.",
    )
    apc_prices: Series[str] | None = pa.Field(
        nullable=True,
        description="APC in various currencies as JSON.",
    )

    # === Metadata ===
    societies: Series[str] | None = pa.Field(
        nullable=True,
        description="Scientific societies joined by '; '.",
    )
    alternate_titles: Series[str] | None = pa.Field(
        nullable=True,
        description="Alternative titles joined by '; '.",
    )
    abbreviated_title: Series[str] | None = pa.Field(
        nullable=True,
        description="Abbreviated title.",
    )
    country_code: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^[A-Z]{2}$",
        description="Country code (for repositories).",
    )

    class Config:
        """Pandera configuration."""

        strict = False
        ordered = True
        coerce = True
