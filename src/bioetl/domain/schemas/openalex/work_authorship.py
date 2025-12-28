"""Pandera schema for OpenAlex Work-Authorship relationship.

Aligned with RULES.md v5.0 and OpenAlex API schema.
See: https://docs.openalex.org/api-entities/works/work-object#authorships
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class OpenAlexWorkAuthorshipSchema(ETLRecordSchema):
    """Work-Authorship relationship schema for Silver layer.

    Represents the 1:N relationship between Works and Authors,
    including institutional affiliations.

    Composite Primary Key: (work_id, author_id, author_sequence_number)
    """

    # === Foreign Keys ===
    work_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
        description="FK to OpenAlexWork.",
    )
    author_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^A\d+$",
        description="FK to OpenAlexAuthor.",
    )

    # === Position ===
    author_position: Series[str] = pa.Field(
        nullable=False,
        isin=["first", "middle", "last"],
        description="Author position in author list.",
    )
    author_sequence_number: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="0-based sequence number.",
    )

    # === Author Info ===
    raw_author_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Author name as it appears in publication.",
    )
    is_corresponding: Series[bool] | None = pa.Field(
        nullable=True,
        description="Corresponding author flag.",
    )

    # === Affiliation (raw) ===
    raw_affiliation_string: Series[str] | None = pa.Field(
        nullable=True,
        description="Primary raw affiliation string.",
    )
    raw_affiliation_strings: Series[str] | None = pa.Field(
        nullable=True,
        description="All raw affiliations joined by ' ||| '.",
    )

    # === Institutions (resolved) ===
    institution_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="OpenAlex Institution IDs joined by '; '.",
    )
    institution_names: Series[str] | None = pa.Field(
        nullable=True,
        description="Institution names joined by '; '.",
    )
    institution_countries: Series[str] | None = pa.Field(
        nullable=True,
        description="Institution country codes joined by '; '.",
    )

    class Config:
        """Pandera configuration."""

        strict = False
        ordered = True
        coerce = True
