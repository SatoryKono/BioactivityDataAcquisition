"""Pandera schema for CrossRef Reference entity.

Bibliographic references extracted from CrossRef Works API 'reference' field.
Aligned with RULES.md v5.0.

Relationship: CrossRefWork 1:N CrossRefReference (citing → cited)
Note: Not all references have resolved DOIs.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pandera as pa
from pandera.typing import Series


class CrossRefReferenceSchema(pa.DataFrameModel):
    """Validation schema for CrossRef Reference records.

    Bibliographic references from publications.
    Layer: Silver (Medallion Architecture)
    Composite Primary Key: (source_doi, reference_key)
    """

    # === Foreign Key (citing work) ===
    source_doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^10\.\d{4,}/.*$",
        description="DOI of the citing work (FK to CrossRefWork).",
    )

    # === Reference Key ===
    reference_key: Series[str] = pa.Field(
        nullable=False,
        description="Unique key of the reference within the source work.",
    )

    # === Resolved Target ===
    target_doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^10\.\d{4,}/.*$",
        description="DOI of the cited work (if resolved).",
    )

    # === Unstructured Citation ===
    unstructured: Series[str] | None = pa.Field(
        nullable=True,
        description="Unstructured citation string.",
    )

    # === Structured Fields ===
    article_title: Series[str] | None = pa.Field(
        nullable=True,
        description="Article title.",
    )
    journal_title: Series[str] | None = pa.Field(
        nullable=True,
        description="Journal title.",
    )
    series_title: Series[str] | None = pa.Field(
        nullable=True,
        description="Series title.",
    )
    volume: Series[str] | None = pa.Field(
        nullable=True,
        description="Volume number.",
    )
    issue: Series[str] | None = pa.Field(
        nullable=True,
        description="Issue number.",
    )
    first_page: Series[str] | None = pa.Field(
        nullable=True,
        description="First page.",
    )
    year: Series[int] | None = pa.Field(
        nullable=True,
        ge=1800,
        le=2030,
        description="Publication year.",
    )
    author: Series[str] | None = pa.Field(
        nullable=True,
        description="First author (Family, Given or just family name).",
    )
    isbn: Series[str] | None = pa.Field(
        nullable=True,
        description="ISBN (for books).",
    )
    issn: Series[str] | None = pa.Field(
        nullable=True,
        description="ISSN.",
    )
    component: Series[str] | None = pa.Field(
        nullable=True,
        description="Component DOI.",
    )
    edition: Series[str] | None = pa.Field(
        nullable=True,
        description="Edition.",
    )
    standards_body: Series[str] | None = pa.Field(
        nullable=True,
        description="Standards body.",
    )

    # === System Fields ===
    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Unique business identifier.",
    )
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[a-f0-9]{64}$",
        description="SHA256 hash for versioning.",
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

        strict = False  # Allow additional columns
        ordered = True  # Enforce column order
        coerce = True  # Coerce data types to match schema
