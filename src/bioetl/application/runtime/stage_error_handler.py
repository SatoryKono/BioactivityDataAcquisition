"""Stage error handler component for managing error policies."""

from collections.abc import Callable
from typing import Any

from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC


class StageErrorHandler:
    """Handles errors according to configured policy and tracks error state."""

    def __init__(
        self,
        *,
        logger: LoggingPortABC,
        provider: str,
        entity_name: str,
        error_policy: ErrorPolicyABC,
        default_on_skip: Callable[[str], Any],
    ) -> None:
        self._logger = logger
        self._provider = provider
        self._entity_name = entity_name
        self._error_policy = error_policy
        self._default_on_skip = default_on_skip
        self._last_error: PipelineStageError | None = None
        self._last_stage_action: dict[str, ErrorAction | None] = {}

    @property
    def last_error(self) -> PipelineStageError | None:
        """Return the last recorded error."""
        return self._last_error

    def set_logger(self, logger: LoggingPortABC) -> None:
        """Update the logger instance."""
        self._logger = logger

    def set_error_policy(self, error_policy: ErrorPolicyABC) -> None:
        """Replace the error policy."""
        self._error_policy = error_policy

    def handle_error(
        self,
        stage: str,
        error: Exception,
        context: RunContext,
        *,
        attempt: int,
    ) -> tuple[ErrorAction, PipelineStageError]:
        """
        Process an error and determine the action.

        Returns tuple of (action, wrapped_error).
        """
        pipeline_error = PipelineStageError(
            provider=self._provider,
            entity=self._entity_name,
            stage=stage,
            attempt=attempt,
            run_id=context.run_id,
            cause=error,
        )
        self._last_error = pipeline_error

        self._logger.error(
            "Stage failed",
            stage=stage,
            provider=self._provider,
            entity=self._entity_name,
            run_id=context.run_id,
            error=str(error),
        )

        action = self._error_policy.handle(pipeline_error, context)
        self._last_stage_action[stage] = action

        return action, pipeline_error

    def should_retry(self, error: PipelineStageError) -> bool:
        """Check if another retry is allowed for the error."""
        return self._error_policy.can_retry(error)

    def log_skip(self, stage: str, context: RunContext, error: Exception) -> None:
        """Log that a stage was skipped due to error policy."""
        self._logger.warning(
            "Stage skipped due to error policy",
            stage=stage,
            provider=self._provider,
            entity=self._entity_name,
            run_id=context.run_id,
            error=str(error),
        )

    def get_skip_value(self, stage: str) -> Any:
        """Return the default value to use when skipping a stage."""
        return self._default_on_skip(stage)

    def clear_error(self) -> None:
        """Clear the last error state (called on successful execution)."""
        self._last_error = None

    def get_last_action(self, stage: str) -> ErrorAction | None:
        """Return the last error action for a stage."""
        return self._last_stage_action.get(stage)

    def get_last_error_messages(self) -> list[str]:
        """Return list of messages from the last error."""
        if self._last_error is None:
            return []

        messages = [str(self._last_error)]
        if self._last_error.cause:
            messages.append(str(self._last_error.cause))
        return messages

    def reset(self) -> None:
        """Clear accumulated error state."""
        self._last_error = None
        self._last_stage_action.clear()

