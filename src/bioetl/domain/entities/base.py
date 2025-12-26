"""Base entity for domain entities.

Contains the BaseEntity class with system fields required for lineage and versioning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID, RunType


@dataclass(frozen=True, kw_only=True)
class BaseEntity:
    """Base class for all domain entities.

    Contains system fields required for lineage and versioning.
    """

    entity_id: EntityID
    content_hash: ContentHash

    # Lineage Metadata
    run_id: RunID
    run_type: RunType
    source_batch_id: BatchID | None = None  # None when batch context unavailable
    ingestion_ts: datetime  # Required: pass context.started_at (ADR-014)

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise ValueError("Entity ID cannot be empty")
        if not self.content_hash:
            raise ValueError("Content hash cannot be empty")
