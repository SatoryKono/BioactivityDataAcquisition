"""Auxiliary metadata and DQ service protocols for application-core helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.application.core.pipeline_observability_service_protocols import (
    PipelineObservabilityServicesProtocol,
)
from bioetl.domain.ports import DQMonitorPort, StorageMaintenancePort

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        SilverDQAnalyzerPort,
    )


@runtime_checkable
class PipelineMetadataServicesProtocol(Protocol):
    """Optional metadata collaborators used after persistence stages."""
    metadata_coordinator: MetadataCoordinatorPort | None
    metadata_writer: MetadataWriterPort | None


@runtime_checkable
class PipelineDQServicesProtocol(Protocol):
    """Optional DQ/reporting collaborators exposed by the aggregate service bag."""
    dq_monitor: DQMonitorPort | None
    bronze_dq_analyzer: BronzeDQAnalyzerPort | None
    silver_dq_analyzer: SilverDQAnalyzerPort | None
    gold_dq_analyzer: GoldDQAnalyzerPort | None
    dq_report_writer: DQReportWriterPort | None
    dq_report_service: DQReportService | None


@runtime_checkable
class PipelineExecutionServicesProtocol(
    PipelineObservabilityServicesProtocol,
    PipelineDQServicesProtocol,
    Protocol,
):
    """Execution surface used by batch/DQ helpers."""


@runtime_checkable
class PipelinePostrunServicesProtocol(
    PipelineObservabilityServicesProtocol,
    PipelineMetadataServicesProtocol,
    Protocol,
):
    """Services surface required by postrun collaborator resolution."""
    storage: StorageMaintenancePort


__all__ = [
    "PipelineDQServicesProtocol",
    "PipelineExecutionServicesProtocol",
    "PipelineMetadataServicesProtocol",
    "PipelinePostrunServicesProtocol",
]
