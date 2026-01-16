"""RunContext value object for pipeline execution context.

Provides an immutable container for run-time context that is shared
across all Medallion layers. This ensures consistency of run_id,
timestamps, and pipeline identification across Bronze, Silver, and Gold.

Implements RULES.md §1 - Domain Layer value objects (frozen dataclass).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.types import RunID, RunType


@dataclass(frozen=True, slots=True)
class RunContext:
    """Immutable context for a pipeline run.

    Contains all information needed to create consistent metadata across
    all Medallion layers. Created once at pipeline start and passed to
    MetadataCoordinator.

    Attributes:
        run_id: Unique identifier for the pipeline run (UUID).
        run_type: Type of run (incremental, backfill, rebuild).
        started_at: UTC timestamp when the run started.
        pipeline_name: Full pipeline name (e.g., 'chembl_activity').
        provider: Data provider name (e.g., 'chembl').
        entity: Entity type (e.g., 'activity').

    Example:
        >>> from datetime import UTC, datetime
        >>> from uuid import uuid4
        >>> context = RunContext(
        ...     run_id=RunID(uuid4()),
        ...     run_type=RunType.INCREMENTAL,
        ...     started_at=datetime.now(UTC),
        ...     pipeline_name="chembl_activity",
        ...     provider="chembl",
        ...     entity="activity",
        ... )
    """

    run_id: RunID
    run_type: RunType
    started_at: datetime
    pipeline_name: str
    provider: str
    entity: str

    def __post_init__(self) -> None:
        """Validate run context after initialization."""
        if self.started_at.tzinfo is None:
            raise ValueError(
                "started_at must be timezone-aware (UTC). "
                "Use datetime.now(UTC) or datetime(..., tzinfo=timezone.utc)."
            )

        if not self.pipeline_name:
            raise ValueError("pipeline_name cannot be empty")

        if not self.provider:
            raise ValueError("provider cannot be empty")

        if not self.entity:
            raise ValueError("entity cannot be empty")

    @classmethod
    def create(
        cls,
        run_id: RunID,
        run_type: RunType,
        started_at: datetime,
        provider: str,
        entity: str,
    ) -> RunContext:
        """Factory method to create RunContext with derived pipeline_name.

        Args:
            run_id: Unique run identifier.
            run_type: Type of pipeline run.
            started_at: UTC timestamp when run started.
            provider: Data provider name.
            entity: Entity type.

        Returns:
            RunContext with pipeline_name derived as '{provider}_{entity}'.
        """
        return cls(
            run_id=run_id,
            run_type=run_type,
            started_at=started_at,
            pipeline_name=f"{provider}_{entity}",
            provider=provider,
            entity=entity,
        )
