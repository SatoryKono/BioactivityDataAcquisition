"""Pandera schema for CrossRef Work entity.

CrossRef Works API provides metadata for scholarly publications with DOIs.
Aligned with RULES.md v5.0 and CrossRef API schema.

API Documentation: https://api.crossref.org/swagger-ui/index.html
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import pandera as pa
from pandera.typing import Series


class CrossRefWorkSchema(pa.DataFrameModel):
    """Validation schema for CrossRef Work (publication) records.

    Core entity representing a publication with DOI in CrossRef registry.
    Layer: Silver (Medallion Architecture)
    Validation: soft (schema drift allowed for optional fields)
    """

    # === Primary Key ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^10\.\d{4,}/.*$",
        description="Digital Object Identifier (primary key, lowercase).",
    )

    # === Required Fields ===
    type: Series[str] = pa.Field(
        nullable=False,
        isin=[
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
        ],
        description="Publication type.",
    )
    title: Series[str] = pa.Field(
        nullable=False,
        description="Publication title (first element of title array).",
    )

    # === System Fields ===
    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Unique business identifier (crossref:{doi}).",
    )
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[a-f0-9]{64}$",
        description="SHA256 hash for SCD Type 2.",
    )

    # === Journal/Book Information ===
    container_title: Series[str] | None = pa.Field(
        nullable=True,
        description="Journal or book title (first element).",
    )
    publisher: Series[str] | None = pa.Field(
        nullable=True,
        description="Publisher name.",
    )
    issn: Series[str] | None = pa.Field(
        nullable=True,
        description="ISSN (first from list, preferably print).",
    )
    isbn: Series[str] | None = pa.Field(
        nullable=True,
        description="ISBN (first from list).",
    )
    volume: Series[str] | None = pa.Field(
        nullable=True,
        description="Volume number.",
    )
    issue: Series[str] | None = pa.Field(
        nullable=True,
        description="Issue number.",
    )
    page: Series[str] | None = pa.Field(
        nullable=True,
        description="Page range (format 'start-end').",
    )

    # === Dates ===
    published_date: Series[date] | None = pa.Field(
        nullable=True,
        description="Publication date (from issued or published-print/online).",
    )
    created_date: Series[date] | None = pa.Field(
        nullable=True,
        description="Date record was created in CrossRef.",
    )
    deposited_date: Series[date] | None = pa.Field(
        nullable=True,
        description="Date of last update in CrossRef.",
    )

    # === Content ===
    abstract: Series[str] | None = pa.Field(
        nullable=True,
        description="Abstract text (may contain HTML entities).",
    )
    language: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^[a-z]{2}$",
        description="Language code (ISO 639-1).",
    )
    subject: Series[str] | None = pa.Field(
        nullable=True,
        description="Subject areas (semicolon-separated).",
    )

    # === Licensing ===
    license_url: Series[str] | None = pa.Field(
        nullable=True,
        description="License URL (first from list).",
    )

    # === Citation Metrics ===
    is_referenced_by_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of citations received.",
    )
    references_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of references in bibliography.",
    )

    # === Funding & Trials ===
    funder_names: Series[str] | None = pa.Field(
        nullable=True,
        description="Funder names (semicolon-separated).",
    )
    clinical_trial_numbers: Series[str] | None = pa.Field(
        nullable=True,
        description="Clinical trial numbers (semicolon-separated).",
    )

    # === Update Policy ===
    update_policy: Series[str] | None = pa.Field(
        nullable=True,
        description="DOI of update policy.",
    )

    # === Lineage Fields (RULES.md §2.4) ===
    _run_id: Series[UUID] = pa.Field(
        nullable=False,
        description="Correlation ID for the pipeline run.",
    )
    _run_type: Series[str] = pa.Field(
        nullable=False,
        isin=["incremental", "backfill", "rebuild"],
        description="Type of pipeline run.",
    )
    _source_batch_id: Series[UUID] | None = pa.Field(
        nullable=True,
        description="Batch context ID from the source.",
    )
    _ingestion_ts: Series[datetime] = pa.Field(
        nullable=False,
        description="Timestamp when the record was ingested (UTC).",
    )

    class Config:
        """Pandera configuration for Silver layer."""

        strict = False  # Allow additional columns (Silver layer flexibility)
        ordered = True  # Enforce column order
        coerce = True  # Coerce data types to match schema
