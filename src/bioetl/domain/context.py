"""Domain context objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bioetl.domain.context_cached_bronze import CachedBronzeContext
from bioetl.domain.context_filtering import InputFilterContext, VacuumConfig
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import ExecutionContext, RunID, RunType

__all__ = [
    "CachedBronzeContext",
    "InputFilterContext",
    "PipelineContext",
    "PipelineRunContext",
    "VacuumConfig",
]


def _now_utc() -> datetime:
    """Factory function for default started_at timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class PipelineContext:
    """Context object for a pipeline run."""

    run_id: RunID
    run_type: RunType
    logger: LoggerPort
    started_at: datetime = field(default_factory=_now_utc)

    @classmethod
    def create(
        cls,
        run_id: RunID,
        run_type: RunType,
        logger: LoggerPort,
        started_at: datetime | None = None,
    ) -> PipelineContext:
        """Create a new PipelineContext with optional automatic timestamp.

        Args:
            run_id: Unique identifier for the pipeline run.
            run_type: Type of run (incremental, backfill, rebuild).
            logger: Structured logger port for pipeline-level logging.
            started_at: Optional UTC start timestamp. Defaults to the current UTC time.

        Returns:
            New PipelineContext instance with all fields set.
        """
        return cls(
            run_id=run_id,
            run_type=run_type,
            logger=logger,
            started_at=started_at or datetime.now(UTC),
        )

    def bind_logger(
        self,
        **kwargs: Any,  # Any: structlog-compatible key=value pairs
    ) -> PipelineContext:
        """Bind additional context to the logger.

        Args:
            **kwargs: Key-value pairs to bind to the structured logger (structlog-compatible).

        Returns:
            New PipelineContext with the bound logger; all other fields unchanged.
        """
        new_logger = self.logger.bind(**kwargs)
        return PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=new_logger,
            started_at=self.started_at,
        )


@dataclass(frozen=True, slots=True)
class PipelineRunContext:
    """Context object encapsulating pipeline launch parameters."""

    pipeline_name: str
    run_id: RunID
    run_type: RunType

    resume: bool = False
    dry_run: bool = False
    vacuum: VacuumConfig = field(default_factory=VacuumConfig)
    input_filter: InputFilterContext = field(
        default_factory=InputFilterContext.disabled
    )
    cached_bronze: CachedBronzeContext = field(
        default_factory=CachedBronzeContext.disabled
    )

    limit: int | None = None
    query: str | None = None
    start_offset: int | None = None
    log_level: str = "INFO"
    ignore_yaml_filter: bool = False
    skip_gold: bool = False
    execution_context: ExecutionContext = ExecutionContext.ISOLATED

    @property
    def has_input_filter(self) -> bool:
        """Check if input filtering is enabled."""
        return self.input_filter.enabled

    @property
    def has_cached_bronze(self) -> bool:
        """Check if cached Bronze mode is enabled."""
        return self.cached_bronze.enabled

    @property
    def vacuum_enabled(self) -> bool | None:
        """Check if vacuum is enabled (tri-state)."""
        return self.vacuum.enabled
