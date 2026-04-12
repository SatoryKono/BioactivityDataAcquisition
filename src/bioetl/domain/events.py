"""Domain Event Constants.

Standardized event names for pipeline observability.
All event logging should use these constants for consistency
and grep-ability across the codebase.

Usage:
    from bioetl.domain.events import PipelineEvent

    logger.info(PipelineEvent.START, run_type=run_type)
    observer.emit_event(PipelineEvent.HEALTH_CHECK_COMPLETED, ...)
"""

from __future__ import annotations

__all__ = [
    "ORDINARY_PIPELINE_STAGE_NAMES",
    "PipelineEvent",
]

ORDINARY_PIPELINE_STAGE_NAMES: tuple[str, ...] = (
    "preflight",
    "prepare_medallion_layers",
    "execute_pipeline",
    "postrun",
    "checkpoint_finalize",
)


class PipelineEvent:
    """Standardized pipeline event names.

    Constants for all structured logging events.
    Using class with class-level strings for simplicity and grep-ability.
    """

    # Pipeline lifecycle events
    START = "pipeline_started"
    COMPLETE = "pipeline_finished"
    FAILED = "pipeline_failed"
    SHUTDOWN = "pipeline_shutdown"

    # Batch processing events
    BATCH_START = "batch_started"
    BATCH_COMPLETE = "batch_completed"

    # Phase events (dynamically suffixed with _started/_completed)
    STARTUP_STARTED = "startup_started"
    STARTUP_COMPLETED = "startup_completed"
    PREFLIGHT_STARTED = "preflight_started"
    PREFLIGHT_COMPLETED = "preflight_completed"
    LIFECYCLE_CLEAR_STARTED = "lifecycle_clear_started"
    LIFECYCLE_CLEAR_COMPLETED = "lifecycle_clear_completed"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    POSTRUN_STARTED = "postrun_started"
    POSTRUN_COMPLETED = "postrun_completed"
    CLEANUP_STARTED = "cleanup_started"
    CLEANUP_COMPLETED = "cleanup_completed"

    # Health check events
    HEALTH_CHECK_COMPLETED = "health_check_completed"
    HEALTH_CHECK_SUMMARY_RECORDED = "health_check_summary_recorded"

    # Data quality events
    DQ_ANOMALY_DETECTED = "dq_anomaly_detected"

    # Maintenance events
    VACUUM_COMPLETED = "vacuum_completed"
    ARTIFACT_PUBLISHED = "artifact_published"

    @classmethod
    def phase_started(cls, phase_value: str) -> str:
        """Generate phase started event name.

        Args:
            phase_value: LifecyclePhase value (e.g., "preflight").

        Returns:
            Event name (e.g., "preflight_started").
        """
        return f"{phase_value}_started"

    @classmethod
    def phase_completed(cls, phase_value: str) -> str:
        """Generate phase completed event name.

        Args:
            phase_value: LifecyclePhase value (e.g., "preflight").

        Returns:
            Event name (e.g., "preflight_completed").
        """
        return f"{phase_value}_completed"
