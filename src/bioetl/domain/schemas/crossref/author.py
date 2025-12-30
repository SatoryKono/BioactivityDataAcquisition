"""Pandera schema for CrossRef Author entity.

Aligned with RULES.md v5.0 and CrossRef REST API.
Represents authors from the "author" field in Works API response.
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
AUTHOR_SEQUENCES = ["first", "additional"]


class AuthorSchema(ETLRecordSchema):
    """CrossRef Author validation schema for Silver layer.

    Represents an author of a CrossRef Work (1:N relationship).
    Composite PK: (doi, author_sequence)
    """

    # === Foreign Key ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^10\.\d{4,}/.*$",
        description="FK to Work.doi",
    )

    # === Composite Primary Key Component ===
    author_sequence: Series[int] = pa.Field(
        nullable=False, ge=0, description="Author order (0-based index)"
    )

    # === Author Names ===
    family_name: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1},
        description="Family name (required)",
    )
    given_name: Series[str] | None = pa.Field(
        nullable=True, description="Given name(s)"
    )
    suffix: Series[str] | None = pa.Field(
        nullable=True, description="Name suffix (Jr., III, etc.)"
    )

    # === Identifiers ===
    orcid: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$",
        description="ORCID (ID only, without URL prefix)",
    )
    authenticated_orcid: Series[bool] | None = pa.Field(
        nullable=True, description="Whether ORCID is CrossRef-authenticated"
    )

    # === Affiliation ===
    affiliation: Series[str] | None = pa.Field(
        nullable=True, description="Primary affiliation (first from affiliations list)"
    )
    affiliation_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Affiliation identifiers (ROR, ISNI; joined with '; ')",
    )

    # === Metadata ===
    sequence: Series[str] | None = pa.Field(
        nullable=True,
        isin=AUTHOR_SEQUENCES,
        description="Author sequence type ('first' or 'additional')",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "AuthorSchema"
        description = "CrossRef Author Silver layer validation"
