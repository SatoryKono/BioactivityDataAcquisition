"""Pipeline Event Names.

Provides standardized event name constants for consistent logging
and observability across the pipeline.

Usage:
    from bioetl.domain.events import PipelineEvent

    logger.info(PipelineEvent.START, extra={...})
"""

from __future__ import annotations


class PipelineEvent:
    """Standardized pipeline event names for logging.

    Ensures consistent event naming across all pipeline components
    for unified observability and log aggregation.
    """

    # Pipeline lifecycle events
    START = "pipeline_start"
    COMPLETE = "pipeline_complete"
    ERROR = "pipeline_error"
    SHUTDOWN = "pipeline_shutdown"

    # Batch processing events
    BATCH_START = "batch_start"
    BATCH_COMPLETE = "batch_complete"

    # Health check events
    HEALTH_CHECK_PASSED = "pipeline_health_check_passed"


__all__ = ["PipelineEvent"]
