"""Pandera schema for CrossRef Funder entity.

Funders extracted from CrossRef Works API 'funder' field.
Integrates with CrossRef Funder Registry.
Aligned with RULES.md v5.0.

Relationship: CrossRefWork 1:N CrossRefFunder
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pandera as pa
from pandera.typing import Series


class CrossRefFunderSchema(pa.DataFrameModel):
    """Validation schema for CrossRef Funder records.

    Funding sources for publications.
    Layer: Silver (Medallion Architecture)
    Composite Primary Key: (doi, funder_sequence)
    """

    # === Foreign Key ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^10\.\d{4,}/.*$",
        description="DOI of the funded work (FK to CrossRefWork).",
    )

    # === Sequence ===
    funder_sequence: Series[int] = pa.Field(
        nullable=False,
        ge=0,
        description="0-based index of funder in the funder list.",
    )

    # === Required Fields ===
    name: Series[str] = pa.Field(
        nullable=False,
        description="Funder organization name.",
    )

    # === Optional Fields ===
    funder_doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^10\.13039/\d+$",
        description="DOI of funder in Funder Registry.",
    )
    funder_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Legacy funder ID (without DOI prefix).",
    )
    award_numbers: Series[str] | None = pa.Field(
        nullable=True,
        description="Grant/award numbers (semicolon-separated).",
    )
    award_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of awards.",
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
