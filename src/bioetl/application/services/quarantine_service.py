"""Quarantine service for administrative operations (Application layer).

Provides high-level quarantine management for CLI and other interfaces.
Uses QuarantinePort for actual persistence operations.
Tracing coverage remains implemented in the split mixins via
``traced_operation`` and ``traced_async_operation``.
The traced operator workflows remain:
``quarantine.inspect``, ``quarantine.stats``, ``quarantine.replay``,
``quarantine.mark_reprocessed``, ``quarantine.purge``, and
``quarantine.update_status``.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

__all__ = ["QuarantineRecord", "QuarantineService"]

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.observability.span_attribute_values import (
    coerce_span_attribute_value,
)
from bioetl.application.services._quarantine_service_async_mixin import (
    QuarantineServiceAsyncMixin,
)
from bioetl.application.services._quarantine_service_filtered_mixin import (
    QuarantineServiceFilteredMixin,
)
from bioetl.application.services._quarantine_service_support import (
    _QUARANTINE_OPERATOR_DURATION_METRIC,
    _QUARANTINE_OPERATOR_OPERATIONS_METRIC,
)
from bioetl.application.services._quarantine_service_sync_mixin import (
    QuarantineServiceSyncMixin,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import LoggerPort, MetricsPort, QuarantinePort, TracingPort


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    """Representation of a quarantined record.

    Attributes:
        error_code: Error code that caused quarantine, or None if unknown.
        payload: Original record data.
        batch_id: Bronze batch ID.
        pipeline: Pipeline name.
        ingestion_ts: When record was quarantined.
        metadata: Additional metadata.
    """

    error_code: str | None
    payload: JsonDict  # Any: quarantine payload has heterogeneous values
    batch_id: str | None
    pipeline: str
    ingestion_ts: datetime | None
    metadata: JsonDict  # Any: metadata values are heterogeneous


@dataclass
class QuarantineService(
    QuarantineServiceFilteredMixin,
    QuarantineServiceAsyncMixin,
    QuarantineServiceSyncMixin,
):
    """Service for administrative quarantine operations.

    Provides high-level operations for quarantine management
    used by CLI and other interfaces. Wraps QuarantinePort
    for Application-layer abstraction.

    Attributes:
        quarantine_port: Port for quarantine persistence.
        logger: Structured logger for observability.

    Example:
        >>> service = QuarantineService(quarantine_port=port, logger=logger)
        >>> records = await service.inspect("chembl_activity", limit=10)
        >>> for rec in records:
        ...     logger.info("quarantine_record", error_code=rec.error_code, payload=rec.payload)
    """

    quarantine_port: QuarantinePort
    logger: LoggerPort
    metrics: MetricsPort | None = None
    tracer: TracingPort | None = None
    TRACER_NAME = "bioetl.quarantine_admin"

    def _trace_attributes(
        self,
        *,
        operation: str,
        pipeline: str | None = None,
        **extra: object,
    ) -> dict[str, object]:
        """Build bounded tracing attributes for quarantine admin operations."""
        attributes: dict[str, object] = {
            "bioetl.component": "quarantine_service",
            "bioetl.operation": operation,
        }
        if pipeline is not None:
            attributes["bioetl.pipeline"] = pipeline
        attributes.update(extra)
        return attributes

    @staticmethod
    def _set_trace_result(
        span: Span,
        *,
        success: bool,
        **extra: object,
    ) -> None:
        """Attach bounded result attributes to an active trace span."""
        span.set_attribute("bioetl.success", success)
        for key, value in extra.items():
            span.set_attribute(key, coerce_span_attribute_value(value))

    def _record_operator_metrics(
        self,
        *,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """Record bounded admin/explorer metrics when a metrics port is available."""
        if self.metrics is None:
            return
        labels = {"operation": operation, "status": status}
        self.metrics.increment_counter(
            _QUARANTINE_OPERATOR_OPERATIONS_METRIC,
            1,
            labels=labels,
        )
        self.metrics.observe_histogram(
            _QUARANTINE_OPERATOR_DURATION_METRIC,
            duration_seconds,
            labels=labels,
        )

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.quarantine_port.aclose()
