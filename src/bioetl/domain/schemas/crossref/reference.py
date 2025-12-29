"""Pandera schema for CrossRef Reference entity.

Aligned with RULES.md v5.0 and CrossRef REST API.
Represents bibliographic references from the "reference" field in Works API response.
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class ReferenceSchema(ETLRecordSchema):
    """CrossRef Reference validation schema for Silver layer.

    Represents a bibliographic reference in a CrossRef Work (1:N relationship).
    Composite PK: (source_doi, reference_key)
    """

    # === Foreign Key ===
    source_doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^10\.\d{4,}/.*$",
        description="DOI of citing work (FK to Work.doi)",
    )

    # === Composite Primary Key Component ===
    reference_key: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1},
        description="Unique reference key within source work",
    )

    # === Target Reference ===
    target_doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^10\.\d{4,}/.*$",
        description="DOI of cited work (if resolved)",
    )
    unstructured: Series[str] | None = pa.Field(
        nullable=True, description="Unstructured citation string"
    )

    # === Bibliographic Details ===
    article_title: Series[str] | None = pa.Field(
        nullable=True, description="Article title"
    )
    journal_title: Series[str] | None = pa.Field(
        nullable=True, description="Journal name"
    )
    series_title: Series[str] | None = pa.Field(
        nullable=True, description="Series name"
    )
    volume: Series[str] | None = pa.Field(nullable=True, description="Volume number")
    issue: Series[str] | None = pa.Field(nullable=True, description="Issue number")
    first_page: Series[str] | None = pa.Field(
        nullable=True, description="First page number"
    )
    year: Series[int] | None = pa.Field(
        nullable=True,
        ge=1800,
        le=2100,
        description="Publication year",
    )
    author: Series[str] | None = pa.Field(
        nullable=True, description="First author (Family, Given or just family)"
    )

    # === Identifiers ===
    isbn: Series[str] | None = pa.Field(nullable=True, description="ISBN (for books)")
    issn: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{3}[\dX]$",
        description="ISSN",
    )
    component: Series[str] | None = pa.Field(
        nullable=True, description="Component DOI"
    )

    # === Additional Metadata ===
    edition: Series[str] | None = pa.Field(nullable=True, description="Edition number")
    standards_body: Series[str] | None = pa.Field(
        nullable=True, description="Standards organization"
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "ReferenceSchema"
        description = "CrossRef Reference Silver layer validation"
