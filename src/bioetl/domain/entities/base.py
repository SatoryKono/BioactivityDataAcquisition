"""Base entity for domain entities.

Contains the BaseEntity class with system fields required for lineage and versioning.

Entity Field Classification (RULES.md §1):
- REQUIRED: Fields that MUST be present (validated in __post_init__)
- LINEAGE: System metadata fields for tracking (run_id, content_hash, etc.)
- API-OPTIONAL: Fields from external APIs that may or may not be present
- COMPUTED: Fields derived from other fields (pchembl_value, etc.)

Design Rationale for Optional Fields:
External API entities (ChEMBL, PubChem, etc.) have many Optional fields because:
1. APIs may not return all fields for every record
2. Different record types have different available fields
3. Data quality varies across sources and time periods

However, each entity MUST validate its domain-specific required fields
in _validate_invariants() to maintain data integrity. BaseEntity.__post_init__()
is the canonical entrypoint for this invariant hook.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID, RunType

__all__ = [
    "BaseEntity",
]


@dataclass(frozen=True, kw_only=True)
class BaseEntity:
    """Base class for all domain entities.

    Contains system fields required for lineage and versioning.
    All fields in this class are REQUIRED (no Optional types).

    Subclasses SHOULD:
    - Override _validate_invariants() for domain-specific validation
    - Document which of their fields are REQUIRED vs API-OPTIONAL
    - Use `field | None` syntax for API-optional fields

    Attributes:
        entity_id: Unique business identifier (REQUIRED, validated)
        content_hash: SHA256 hash for versioning (REQUIRED, validated)
        run_id: Pipeline run correlation ID (REQUIRED)
        run_type: Type of run for merge priority (REQUIRED)
        source_batch_id: Batch context ID (OPTIONAL, may be None)
        ingestion_ts: Ingestion timestamp from context (REQUIRED)
        _index: Sequential index of the record in the pipeline run.
        _dq_warn: Data quality warning flag (default: False)
        _dq_error: Data quality error flag (default: False)
    """

    # REQUIRED: Business identity
    entity_id: EntityID
    content_hash: ContentHash

    # REQUIRED: Lineage metadata
    run_id: RunID
    run_type: RunType
    ingestion_ts: datetime  # Required: pass context.started_at (ADR-014)
    _index: int  # Sequential index of the record in the pipeline run

    # OPTIONAL: Batch context (None when batch context unavailable)
    source_batch_id: BatchID | None = None

    # DQ flags (Data Quality flags) - applied during transformation
    # These fields track data quality warnings and errors at the record level
    _dq_warn: bool = False  # Record has data quality warnings
    _dq_error: bool = False  # Record has data quality errors

    def __post_init__(self) -> None:
        """Validate shared system fields, then run subclass invariants."""
        if not self.entity_id:
            raise ValueError("Entity ID cannot be empty")
        if not self.content_hash:
            raise ValueError("Content hash cannot be empty")
        if self._index < 0:
            raise ValueError("_index cannot be negative")
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Hook for subclass-specific domain invariants."""
