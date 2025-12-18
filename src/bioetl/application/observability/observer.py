"""Pipeline Observer Context Manager.

Handles automated metrics collection for pipeline execution.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from bioetl.application.core.shutdown import PipelineShutdownError

if TYPE_CHECKING:
    from types import TracebackType

    import structlog

    from bioetl.domain.ports import MetricsPort


class PipelineObserver:
    """
    Context manager for observing pipeline execution.
    Automatically handles timing and metrics submission.

    Usage:
        with PipelineObserver(metrics, logger, "my_pipeline", "incremental") as obs:
            ...
            if shutdown:
                obs.set_status("shutdown")
    """

    def __init__(
        self,
        metrics: MetricsPort,
        logger: structlog.BoundLogger,
        pipeline_name: str,
        run_type: str,
        tags: dict[str, str] | None = None,
    ) -> None:
        self._metrics = metrics
        self._logger = logger
        self._pipeline_name = pipeline_name
        self._run_type = run_type
        self._tags = tags or {}
        self._start_time: float | None = None
        self._status: str | None = None

    def __enter__(self) -> PipelineObserver:
        self._start_time = time.monotonic()
        return self

    def set_status(self, status: str) -> None:
        """Manually set the execution status (e.g., 'shutdown')."""
        self._status = status

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._start_time is None:
            return

        duration = time.monotonic() - self._start_time

        # Determine status
        if self._status:
            status = self._status
        elif exc_val:
            status = "failure"
            if isinstance(exc_val, PipelineShutdownError):
                status = "shutdown"
        else:
            status = "success"

        # Prepare labels
        labels = {
            "pipeline_name": self._pipeline_name,
            "run_type": self._run_type,
            "status": status,
        }
        labels.update(self._tags)

        # Record metrics
        try:
            self._metrics.observe_histogram(
                "pipeline_duration_seconds",
                duration,
                labels,
            )
        except Exception as e:
            self._logger.error(f"Failed to record metrics: {e}", exc_info=True)

        # Log completion summary
        if status == "success":
            self._logger.info(
                "Pipeline completed successfully",
                extra={
                    "stage": "complete",
                    "duration_seconds": duration,
                },
            )
        elif status == "shutdown":
            self._logger.warning(
                "Pipeline shutdown",
                extra={
                    "stage": "shutdown",
                    "duration_seconds": duration,
                },
            )
        else:
            # For failure, the exception usually bubbles up and is logged elsewhere or by the caller.
            # But the observer can log a summary too.
            # However, looking at the Runner, it logs "Pipeline failed" inside the except block BEFORE re-raising.
            # The Observer's __exit__ runs *before* the exception bubbles up further?
            # Actually __exit__ runs, returns False (propagate), then exception propagates.
            pass
