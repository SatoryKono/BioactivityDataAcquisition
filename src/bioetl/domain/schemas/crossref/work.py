"""Pandera schema for CrossRef Work entity.

Aligned with RULES.md v5.0 and CrossRef REST API.
Source: https://api.crossref.org/swagger-ui/index.html
"""

from __future__ import annotations

from datetime import date

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
WORK_TYPES = [
    "journal-article",
    "book-chapter",
    "proceedings-article",
    "book",
    "dataset",
    "report",
    "standard",
    "peer-review",
    "component",
    "posted-content",
    "monograph",
    "reference-entry",
    "dissertation",
    "other",
    "journal-issue",
    "journal",
    "reference-book",
    "book-series",
    "edited-book",
    "book-set",
    "book-part",
    "book-section",
    "book-track",
    "proceedings",
    "proceedings-series",
    "report-series",
    "report-component",
    "grant",
]


class WorkSchema(ETLRecordSchema):
    """CrossRef Work validation schema for Silver layer.

    Represents a publication (article, book, dataset, etc.) with DOI.
    """

    # === Primary Key ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^10\.\d{4,}/.*$",
        description="Digital Object Identifier (PK)",
    )

    # === Core Fields ===
    type: Series[str] = pa.Field(
        nullable=False,
        isin=WORK_TYPES,
        description="Work type (journal-article, book-chapter, etc.)",
    )
    title: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1},
        description="Work title (first element of title array)",
    )

    # === Container (Journal/Book) ===
    container_title: Series[str] | None = pa.Field(
        nullable=True, description="Journal or book name"
    )
    publisher: Series[str] | None = pa.Field(
        nullable=True, description="Publisher name"
    )
    issn: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{3}[\dX]$",
        description="ISSN (print preferred)",
    )
    isbn: Series[str] | None = pa.Field(
        nullable=True, description="ISBN (first from list)"
    )

    # === Volume/Issue/Pages ===
    volume: Series[str] | None = pa.Field(nullable=True, description="Volume number")
    issue: Series[str] | None = pa.Field(nullable=True, description="Issue number")
    page: Series[str] | None = pa.Field(
        nullable=True, description="Page range (format: start-end)"
    )

    # === Dates ===
    published_date: Series[date] | None = pa.Field(
        nullable=True, description="Publication date (from issued or published-print)"
    )
    created_date: Series[date] | None = pa.Field(
        nullable=True, description="Record creation date in CrossRef"
    )
    deposited_date: Series[date] | None = pa.Field(
        nullable=True, description="Last update date in CrossRef"
    )

    # === Content ===
    abstract: Series[str] | None = pa.Field(
        nullable=True, description="Abstract text (may contain HTML entities)"
    )
    language: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^[a-z]{2}$",
        description="Language code (ISO 639-1)",
    )
    subject: Series[str] | None = pa.Field(
        nullable=True, description="Subject areas (joined with '; ')"
    )

    # === License & Access ===
    license_url: Series[str] | None = pa.Field(
        nullable=True, description="License URL (first from list)"
    )

    # === Citation Metrics ===
    is_referenced_by_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Citation count (times referenced)"
    )
    references_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Reference count (bibliography size)"
    )

    # === Funding & Clinical Trials ===
    funder_names: Series[str] | None = pa.Field(
        nullable=True, description="Funder names (joined with '; ')"
    )
    clinical_trial_numbers: Series[str] | None = pa.Field(
        nullable=True, description="Clinical trial identifiers (joined with '; ')"
    )

    # === Policies ===
    update_policy: Series[str] | None = pa.Field(
        nullable=True, description="DOI of update policy"
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "WorkSchema"
        description = "CrossRef Work Silver layer validation"
