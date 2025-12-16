"""Domain context objects."""

from dataclasses import dataclass
from typing import Any, Protocol

from bioetl.domain.types import RunID, RunType


class BoundLogger(Protocol):
    """Protocol for structured loggers with bind capability.

    This allows the domain layer to work with structlog without importing it.
    """

    def bind(self, **kwargs: Any) -> "BoundLogger":
        """Bind additional context to the logger."""
        ...

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log info message."""
        ...

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log error message."""
        ...

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log debug message."""
        ...

    def exception(self, msg: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        ...


@dataclass(frozen=True)
class PipelineContext:
    """Context object for a pipeline run.

    Provides a consistent set of metadata to all pipeline components.
    """

    run_id: RunID
    run_type: RunType
    logger: BoundLogger

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
