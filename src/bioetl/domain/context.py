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
