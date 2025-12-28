"""Pandera schema for CrossRef Author entity.

Authors extracted from CrossRef Works API 'author' field.
Aligned with RULES.md v5.0.

Relationship: CrossRefWork 1:N CrossRefAuthor
Foreign Key: doi → CrossRefWork.doi
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pandera as pa
from pandera.typing import Series


class CrossRefAuthorSchema(pa.DataFrameModel):
    """Validation schema for CrossRef Author records.

    Authors of publications with DOIs.
    Layer: Silver (Medallion Architecture)
    Composite Primary Key: (doi, author_sequence)
    """

    # === Foreign Key ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^10\.\d{4,}/.*$",
        description="DOI of the parent work (FK to CrossRefWork).",
    )

    # === Sequence ===
    author_sequence: Series[int] = pa.Field(
        nullable=False,
        ge=0,
        description="0-based index of author in the author list.",
    )

    # === Required Fields ===
    family_name: Series[str] = pa.Field(
        nullable=False,
        description="Author family name (surname).",
    )

    # === Optional Fields ===
    given_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Author given name (first name).",
    )
    orcid: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$",
        description="ORCID identifier (without URL prefix).",
    )
    affiliation: Series[str] | None = pa.Field(
        nullable=True,
        description="First affiliation name.",
    )
    affiliation_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Affiliation identifiers (ROR, ISNI) semicolon-separated.",
    )
    authenticated_orcid: Series[bool] | None = pa.Field(
        nullable=True,
        description="Whether ORCID was verified by CrossRef.",
    )
    sequence: Series[str] | None = pa.Field(
        nullable=True,
        isin=["first", "additional"],
        description="Author sequence type.",
    )
    suffix: Series[str] | None = pa.Field(
        nullable=True,
        description="Name suffix (Jr., III, etc.).",
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
