"""Pipeline configuration - immutable data container.

Part of BasePipeline decomposition (ADR-0005).
Separates static configuration from runtime behavior.
"""

from dataclasses import dataclass

from bioetl.domain.types import RunType


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable pipeline configuration.

    Contains static configuration that doesn't change during execution.
    Frozen dataclass ensures immutability after creation.

    Attributes:
        pipeline_name: Unique identifier (e.g., 'chembl_activity').
        provider: Data source provider (e.g., 'chembl').
        entity_type: Entity being processed (e.g., 'activity').
        primary_keys: Primary key columns for Silver layer merge.
        silver_table: Silver layer table name.
        gold_table: Gold layer table name (optional).
        batch_size: Records per batch for processing.
        checkpoint_interval: Records between checkpoint saves.

    Example:
        >>> config = PipelineConfig(
        ...     pipeline_name="chembl_activity",
        ...     provider="chembl",
        ...     entity_type="activity",
        ...     primary_keys=["activity_id"],
        ...     silver_table="chembl_activity",
        ... )
    """

    pipeline_name: str
    provider: str
    entity_type: str
    primary_keys: list[str]
    silver_table: str
    gold_table: str | None = None
    batch_size: int = 100
    checkpoint_interval: int = 1000
    heartbeat_interval: float = 20.0

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        if not self.pipeline_name:
            raise ValueError("pipeline_name cannot be empty")
        if not self.provider:
            raise ValueError("provider cannot be empty")
        if not self.entity_type:
            raise ValueError("entity_type cannot be empty")
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {self.batch_size}")
        if self.checkpoint_interval <= 0:
            raise ValueError(
                f"checkpoint_interval must be positive, got {self.checkpoint_interval}"
            )
        if not self.primary_keys:
            raise ValueError("primary_keys cannot be empty")

    @property
    def lock_key(self) -> str:
        """Generate lock key for distributed locking."""
        return f"pipeline:{self.pipeline_name}"


@dataclass(frozen=True)
class PipelineRuntimeConfig:
    """Runtime execution parameters.

    Contains parameters that may vary between pipeline runs
    but are fixed during a single execution.

    Attributes:
        run_type: Execution mode (incremental/backfill/rebuild).
        resume: Whether to resume from last checkpoint.
        limit: Maximum records to process (None = unlimited).
    """

    run_type: RunType
    resume: bool = False
    limit: int | None = None

    def __post_init__(self) -> None:
        """Validate runtime config."""
        if self.limit is not None and self.limit <= 0:
            raise ValueError(f"limit must be positive or None, got {self.limit}")
