"""Composite lifecycle publication service.

Owns composite runtime lifecycle publication so runner internals do not emit
PipelineEvent lifecycle records directly through LoggerPort.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.events import PipelineEvent
from bioetl.domain.ports import LoggerPort

__all__ = ["CompositeLifecycleObserverService"]


@dataclass(frozen=True, slots=True)
class CompositeLifecycleObserverService:
    """Emit canonical composite lifecycle events through LoggerPort."""

    logger: LoggerPort

    def emit_run_started(self, *, composite_name: str, run_id: str) -> None:
        """Emit the canonical composite run start event."""
        self.logger.info(
            PipelineEvent.START,
            composite=composite_name,
            run_id=run_id,
            stage="composite_start",
        )

    def emit_run_failed(
        self,
        *,
        composite_name: str,
        run_id: str,
        error: Exception,
        reason_code: str,
        stage: str | None = None,
    ) -> None:
        """Emit the canonical composite run failure event."""
        log_kwargs: dict[str, object] = {
            "composite": composite_name,
            "run_id": run_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "reason_code": reason_code,
        }
        if stage is not None:
            log_kwargs["stage"] = stage
        self.logger.error(PipelineEvent.FAILED, **log_kwargs)

    def emit_run_shutdown(
        self,
        *,
        composite_name: str,
        run_id: str,
        error: Exception,
        reason: str,
        reason_code: str,
    ) -> None:
        """Emit the canonical composite shutdown event."""
        self.logger.warning(
            PipelineEvent.SHUTDOWN,
            composite=composite_name,
            run_id=run_id,
            error=str(error),
            error_type=type(error).__name__,
            reason=reason,
            reason_code=reason_code,
        )

    def emit_phase_started(
        self,
        *,
        composite_name: str,
        run_id: str,
        phase_name: str,
        details: dict[str, object] | None = None,
    ) -> None:
        """Emit one composite phase-start lifecycle event."""
        log_kwargs: dict[str, object] = {
            "composite": composite_name,
            "run_id": run_id,
        }
        log_kwargs.update(details or {})
        self.logger.info(
            PipelineEvent.phase_started(phase_name),
            **log_kwargs,
        )

    def emit_phase_completed(
        self,
        *,
        composite_name: str,
        run_id: str,
        phase_name: str,
        details: dict[str, object] | None = None,
    ) -> None:
        """Emit one composite phase-complete lifecycle event."""
        log_kwargs: dict[str, object] = {
            "composite": composite_name,
            "run_id": run_id,
        }
        log_kwargs.update(details or {})
        self.logger.info(
            PipelineEvent.phase_completed(phase_name),
            **log_kwargs,
        )

    def emit_run_completed(
        self,
        *,
        composite_name: str,
        run_id: str,
        duration_seconds: float,
        had_warnings: bool,
    ) -> None:
        """Emit the canonical composite run completion event."""
        log_kwargs: dict[str, object] = {
            "composite": composite_name,
            "run_id": run_id,
            "duration_seconds": duration_seconds,
        }
        if had_warnings:
            log_kwargs["status"] = "completed_with_warnings"
            log_kwargs["had_warnings"] = True
        self.logger.info(PipelineEvent.COMPLETE, **log_kwargs)
