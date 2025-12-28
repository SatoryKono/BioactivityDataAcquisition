"""Pandera schema for OpenAlex Work-MeSH relationship.

Aligned with RULES.md v5.0 and OpenAlex API schema.
See: https://docs.openalex.org/api-entities/works/work-object#mesh
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class OpenAlexWorkMeshSchema(ETLRecordSchema):
    """Work-MeSH relationship schema for Silver layer.

    Represents the 1:N relationship between Works and MeSH descriptors.
    MeSH terms are only present for works indexed in PubMed.

    Composite Primary Key: (work_id, descriptor_ui, qualifier_ui)
    Note: qualifier_ui may be NULL.
    """

    # === Foreign Key ===
    work_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
        description="FK to OpenAlexWork.",
    )

    # === MeSH Descriptor ===
    descriptor_ui: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^D\d{6,9}$",
        description="MeSH Descriptor UI (e.g., D000818).",
    )
    descriptor_name: Series[str] = pa.Field(
        nullable=False,
        description="MeSH Descriptor Name.",
    )

    # === MeSH Qualifier (optional) ===
    qualifier_ui: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^Q\d{6,9}$",
        description="MeSH Qualifier UI (e.g., Q000235).",
    )
    qualifier_name: Series[str] | None = pa.Field(
        nullable=True,
        description="MeSH Qualifier Name.",
    )

    # === Flags ===
    is_major_topic: Series[bool] | None = pa.Field(
        nullable=True,
        description="Major topic flag.",
    )

    class Config:
        """Pandera configuration."""

        strict = False
        ordered = True
        coerce = True
