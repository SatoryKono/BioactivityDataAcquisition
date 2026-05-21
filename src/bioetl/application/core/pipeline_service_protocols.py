"""Protocol contracts for application-core pipeline service bundles."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Protocol, Self, runtime_checkable

from bioetl.domain.ports import (
    BronzeStoragePort,
    CheckpointPort,
    DataSourcePort,
    DQMonitorPort,
    GoldStoragePort,
    LockPort,
    LoggerPort,
    MergedStoragePort,
    MetricsPort,
    QuarantinePort,
    SilverStoragePort,
    StorageLifecyclePort,
    StorageMaintenancePort,
    TracingPort,
)

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
class PipelineStorageProtocol(
    BronzeStoragePort,
    SilverStoragePort,
    GoldStoragePort,
    MergedStoragePort,
    StorageMaintenancePort,
    StorageLifecyclePort,
    Protocol,
):
    """Application DI contract for a full pipeline storage adapter."""


@runtime_checkable
class PipelineServicesProtocol(Protocol):
    """Structural contract for the injected application-core service bundle."""

    data_source: DataSourcePort
    storage: PipelineStorageProtocol
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    tracing: TracingPort
    logger: LoggerPort
    dq_monitor: DQMonitorPort | None
    metadata_coordinator: MetadataCoordinatorPort | None
    metadata_writer: MetadataWriterPort | None
    bronze_dq_analyzer: BronzeDQAnalyzerPort | None
    silver_dq_analyzer: SilverDQAnalyzerPort | None
    gold_dq_analyzer: GoldDQAnalyzerPort | None
    dq_report_writer: DQReportWriterPort | None
    dq_report_service: DQReportService | None

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    async def aclose(self) -> None: ...


__all__ = ["PipelineServicesProtocol", "PipelineStorageProtocol"]
