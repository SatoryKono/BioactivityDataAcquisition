"""Domain context objects."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import RunID, RunType

# Backward compatibility alias
BoundLogger = LoggerPort


def _now_utc() -> datetime:
    """Factory function for default started_at timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class PipelineContext:
    """Context object for a pipeline run.

    Provides a consistent set of metadata to all pipeline components.
    The started_at field is the single source of truth for timestamps
    within a pipeline run (see ADR-014).
    """

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
    ) -> "PipelineContext":
        """Create a new PipelineContext with optional automatic timestamp.

        Args:
            run_id: Unique identifier for the pipeline run
            run_type: Type of run (incremental, backfill, rebuild)
            logger: Structured logger for observability
            started_at: Optional timestamp; if None, uses current UTC time

        Returns:
            New PipelineContext instance
        """
        return cls(
            run_id=run_id,
            run_type=run_type,
            logger=logger,
            started_at=started_at or datetime.now(UTC),
        )

    def bind_logger(self, **kwargs: Any) -> "PipelineContext":
        """Bind additional context to the logger.

        Returns a new context with the bound logger.
        """
        new_logger = self.logger.bind(**kwargs)
        return PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=new_logger,
            started_at=self.started_at,
        )


@dataclass(frozen=True)
class PipelineRunContext:
    """Context object encapsulating pipeline launch parameters.

    Used to pass runtime arguments from CLI/Orchestrator to the Composition Root.
    """

    pipeline_name: str
    run_id: RunID
    run_type: RunType
    resume: bool = False
    limit: int | None = None
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    query: str | None = None
    dry_run: bool = False
