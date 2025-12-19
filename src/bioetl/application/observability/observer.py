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
        self._logger.info(
            f"Starting pipeline: {self._pipeline_name}",
            extra={"stage": "startup", "run_type": self._run_type},
        )
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
            "pipeline": self._pipeline_name,
            "stage": "pipeline",  # Overall pipeline duration
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
        extra = {
            "stage": "complete" if status == "success" else status,
            "duration_seconds": duration,
        }

        if status == "success":
            self._logger.info("Pipeline completed successfully", extra=extra)
        elif status == "shutdown":
            self._logger.warning("Pipeline shutdown", extra=extra)
        elif status == "failure":
             # We log failure here to ensure visibility even if exception handling in caller is silent
             self._logger.error(
                 "Pipeline failed",
                 extra={**extra, "error": str(exc_val)},
                 exc_info=(exc_type, exc_val, exc_tb)
             )
