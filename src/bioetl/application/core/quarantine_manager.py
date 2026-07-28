"""Runtime quarantine service for ETL pipelines.

Refactored per ADR-005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

from typing import NamedTuple

from bioetl.application.core._quarantine_manager_support import (
    QuarantineManagerSupportMixin,
)
from bioetl.application.observability.domain_event_emitter import (
    DomainEventEmitterProtocol,
)
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.ports import MetricsPort, QuarantinePort
from bioetl.domain.types import BronzeRecord, ErrorType, JsonDict

from .batch_metrics import BatchMetricsRecorderService


class DQQuarantineEntry(NamedTuple):
    """A record that failed data-quality checks."""

    record: BronzeRecord
    error_type: ErrorType
    error_details: str

class FilteredQuarantineEntry(NamedTuple):
    """A record excluded by Silver filters."""

    record: BronzeRecord
    reason: str
    details: JsonDict | None = None

class QuarantineRuntimeService(QuarantineManagerSupportMixin):
    """Write records that fail processing to quarantine storage.

    Admin/operator inspection and purge workflows live in
    ``application.services.quarantine_service.QuarantineService``.
    """

    def __init__(
        self,
        quarantine_port: QuarantinePort,
        pipeline_name: str,
        metrics: MetricsPort | None = None,
        pipeline_metrics: PipelineMetricsRecorder | None = None,
        batch_metrics: BatchMetricsRecorderService | None = None,
        run_type: str = "unknown",
        domain_event_emitter: DomainEventEmitterProtocol | None = None,
    ) -> None:
        """Initialize QuarantineRuntimeService with explicit dependencies.

        Args:
            quarantine_port: Port for writing to quarantine storage.
            pipeline_name: Name of the pipeline for identification.
            metrics: Optional metrics port for incrementing quarantine record
                counters per pipeline and error reason.
            pipeline_metrics: Optional prebuilt pipeline-scoped metrics recorder.
            batch_metrics: Optional run-type-aware recorder shared with batch processing.
            run_type: Run type label used by fallback direct metric emissions.

        """
        self._quarantine = quarantine_port
        self._pipeline_name = pipeline_name
        self._metrics = metrics
        self._batch_metrics = batch_metrics
        self._run_type = run_type
        resolved_pipeline_metrics = pipeline_metrics
        if resolved_pipeline_metrics is None:
            resolved_pipeline_metrics = PipelineMetricsRecorder(
                metrics,
                pipeline_name,
            )
        self._pipeline_metrics = resolved_pipeline_metrics
        self._domain_event_emitter = domain_event_emitter

__all__ = [
    "DQQuarantineEntry",
    "FilteredQuarantineEntry",
    "QuarantineRuntimeService",
]
