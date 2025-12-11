"""Runtime context for pipeline execution.

This module provides a context object that encapsulates all runtime
dependencies needed during pipeline execution, including observability,
error handling, and state management.

The context follows the Context Object pattern, reducing the number
of parameters passed to individual stage methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.observability.contracts import LoggingPortABC, MetricsPortABC
    from bioetl.domain.pipelines.contracts import ErrorPolicyABC


@dataclass
class PipelineRuntimeContext:
    """Runtime context for pipeline execution.

    Encapsulates all cross-cutting concerns needed during pipeline execution,
    including logging, metrics, error handling, and shared state.

    The context can create child contexts bound to specific stages,
    automatically enriching logs with stage information.

    Example:
        >>> context = PipelineRuntimeContext(
        ...     run_id="run-123",
        ...     logger=logger,
        ...     metrics=metrics,
        ...     error_policy=fail_fast_policy,
        ... )
        >>> stage_context = context.for_stage("extract")
        >>> stage_context.logger.info("Starting extraction")
    """

    run_id: str
    logger: "LoggingPortABC"
    metrics: "MetricsPortABC"
    error_policy: "ErrorPolicyABC"
    dry_run: bool = False
    state: dict[str, Any] = field(default_factory=dict)
    current_stage: str | None = None

    def for_stage(self, stage_name: str) -> "PipelineRuntimeContext":
        """Create child context bound to specific stage.

        Creates a new context with the logger bound to the stage name,
        enabling automatic stage identification in log messages.

        Args:
            stage_name: Name of the stage for context binding.

        Returns:
            New context with stage-bound logger.

        Example:
            >>> extract_context = context.for_stage("extract")
            >>> extract_context.logger.info("Processing chunk")
            # Logs: {"stage": "extract", "message": "Processing chunk", ...}
        """
        return PipelineRuntimeContext(
            run_id=self.run_id,
            logger=self.logger.apply_bind(stage=stage_name),
            metrics=self.metrics,
            error_policy=self.error_policy,
            dry_run=self.dry_run,
            state={**self.state},
            current_stage=stage_name,
        )

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from shared state.

        Args:
            key: State key.
            default: Value to return if key not found.

        Returns:
            State value or default.
        """
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Set value in shared state.

        Args:
            key: State key.
            value: Value to store.
        """
        self.state[key] = value

    def update_state(self, **kwargs: Any) -> None:
        """Update multiple state values.

        Args:
            **kwargs: Key-value pairs to update.
        """
        self.state.update(kwargs)

    def should_skip_stage(self, stage_name: str, skip_on_dry_run: bool) -> bool:
        """Determine if a stage should be skipped.

        Args:
            stage_name: Name of the stage.
            skip_on_dry_run: Whether stage should skip in dry run mode.

        Returns:
            True if stage should be skipped.
        """
        if self.dry_run and skip_on_dry_run:
            self.logger.info(
                f"Skipping stage '{stage_name}' in dry run mode",
                extra={"stage": stage_name, "reason": "dry_run"},
            )
            return True
        return False


@dataclass
class StageExecutionState:
    """State tracking for a single stage execution.

    Tracks progress, timing, and results for a pipeline stage.

    Attributes:
        stage_name: Name of the stage.
        started: Whether execution has started.
        completed: Whether execution has completed.
        success: Whether execution was successful.
        records_processed: Number of records processed.
        chunks_processed: Number of chunks processed.
        errors: List of error messages encountered.
    """

    stage_name: str
    started: bool = False
    completed: bool = False
    success: bool = False
    records_processed: int = 0
    chunks_processed: int = 0
    errors: list[str] = field(default_factory=list)

    def mark_started(self) -> None:
        """Mark stage as started."""
        self.started = True

    def mark_completed(self, success: bool = True) -> None:
        """Mark stage as completed.

        Args:
            success: Whether stage completed successfully.
        """
        self.completed = True
        self.success = success

    def add_error(self, error: str) -> None:
        """Add error message.

        Args:
            error: Error description.
        """
        self.errors.append(error)

    def increment_records(self, count: int) -> None:
        """Increment processed records count.

        Args:
            count: Number of records to add.
        """
        self.records_processed += count

    def increment_chunks(self) -> None:
        """Increment processed chunks count."""
        self.chunks_processed += 1


__all__ = [
    "PipelineRuntimeContext",
    "StageExecutionState",
]
