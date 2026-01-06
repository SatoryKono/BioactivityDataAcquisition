"""Pandera schema for CrossRef Funder entity.

Aligned with RULES.md v5.0 and CrossRef REST API.
Represents funders from the "funder" field in Publications API response.
Integrates with CrossRef Funder Registry (DOI prefix: 10.13039/).

Terminology:
- Uses "Publication" instead of CrossRef API term "Work" for Ubiquitous Language
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class FunderSchema(ETLRecordSchema):
    """CrossRef Funder validation schema for Silver layer.

    Represents a funder of a CrossRef Publication (1:N relationship).
    Composite PK: (doi, funder_sequence)
    """

    # === Foreign Key ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^10\.\d{4,}/.*$",
        description="FK to Publication.doi",
    )

    # === Composite Primary Key Component ===
    funder_sequence: Series[int] = pa.Field(
        nullable=False, ge=0, description="Funder order (0-based index)"
    )

    # === Funder Details ===
    name: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1},
        description="Funder organization name",
    )
    funder_doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^10\.13039/\d+$",
        description="Funder Registry DOI (10.13039/...)",
    )
    funder_id: Series[str] | None = pa.Field(
        nullable=True, description="Funder ID (legacy, without DOI prefix)"
    )

    # === Awards/Grants ===
    award_numbers: Series[str] | None = pa.Field(
        nullable=True, description="Grant/award numbers (joined with '; ')"
    )
    award_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of awards from this funder"
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "FunderSchema"
        description = "CrossRef Funder Silver layer validation"
