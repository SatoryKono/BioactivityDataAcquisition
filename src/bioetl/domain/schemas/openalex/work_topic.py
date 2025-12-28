"""Pandera schema for OpenAlex Work-Topic relationship.

Aligned with RULES.md v5.0 and OpenAlex API schema.
See: https://docs.openalex.org/api-entities/works/work-object#topics
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class OpenAlexWorkTopicSchema(ETLRecordSchema):
    """Work-Topic relationship schema for Silver layer.

    Represents the 1:N relationship between Works and Topics.
    Topics are the new OpenAlex taxonomy (replacing deprecated concepts).

    Composite Primary Key: (work_id, topic_id)
    """

    # === Foreign Keys ===
    work_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
        description="FK to OpenAlexWork.",
    )
    topic_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^T\d+$",
        description="Topic ID.",
    )

    # === Score ===
    score: Series[float] = pa.Field(
        nullable=False,
        ge=0,
        le=1,
        description="Topic relevance score (0-1).",
    )

    # === Topic Hierarchy ===
    topic_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Topic display name.",
    )
    subfield_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Subfield ID.",
    )
    subfield_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Subfield name.",
    )
    field_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Field ID.",
    )
    field_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Field name.",
    )
    domain_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Domain ID.",
    )
    domain_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Domain name.",
    )

    class Config:
        """Pandera configuration."""

        strict = False
        ordered = True
        coerce = True
