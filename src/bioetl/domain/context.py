"""Domain context objects."""

from dataclasses import dataclass
from typing import Any

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import RunID, RunType

# Backward compatibility alias
BoundLogger = LoggerPort


@dataclass(frozen=True)
class PipelineContext:
    """Context object for a pipeline run.

    Provides a consistent set of metadata to all pipeline components.
    """

    run_id: RunID
    run_type: RunType
    logger: LoggerPort

    def bind_logger(self, **kwargs: Any) -> "PipelineContext":
        """Bind additional context to the logger.

        Returns a new context with the bound logger.
        """
        new_logger = self.logger.bind(**kwargs)
        return PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=new_logger,
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
