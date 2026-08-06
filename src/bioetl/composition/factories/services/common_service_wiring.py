# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Internal wiring helpers for common pipeline service ports."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast, TYPE_CHECKING, Protocol, cast

from bioetl.composition.factories.dq._context_resolver_support import DQServiceBundle
from bioetl.composition.factories.services.port_factories import (
    create_checkpoint,
    create_lock,
    create_metrics,
    create_quarantine,
)
from bioetl.composition.observability_resolution import (
    resolve_tracing_port as _resolve_tracing_port,
)
from bioetl.domain.ports.noop import NoOpAudit

if TYPE_CHECKING:
    from bioetl.application.core.wiring.runtime import (
        PipelineService,
        PipelineStorageProtocol,
    )
    from bioetl.application.services.quality.dq_report_service import DQReportService
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import (
        AuditPort,
        BronzeDQAnalyzerPort,
        CheckpointPort,
        DataSourcePort,
        DQMonitorPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
        SettingsPort,
        SilverDQAnalyzerPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.composition.factories.storage import StorageContext
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class _StorageFactoryProtocol(Protocol):
    """Structural contract shared by the lazy and concrete storage factories."""

    @staticmethod
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort,
        audit: AuditPort,
        tracing: TracingPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
        pipeline_name: str | None = None,
    ) -> StorageContext: ...


class _LazyStorageFactory:
    """Patchable storage factory seam without importing storage at module load."""

    @staticmethod
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort,
        audit: AuditPort,
        tracing: TracingPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
        pipeline_name: str | None = None,
    ) -> StorageContext:
        from bioetl.composition.factories.storage import StorageFactory

        return StorageFactory.create(
            settings,
            config,
            logger,
            metrics=metrics,
            audit=audit,
            tracing=tracing,
            metadata_coordinator=metadata_coordinator,
            silver_validator=silver_validator,
            pipeline_name=pipeline_name,
        )


StorageFactory = _LazyStorageFactory


def _create_metrics_from_settings(settings: Settings) -> MetricsPort:
    return create_metrics(cast("SettingsPort", settings))


def _create_checkpoint_for_storage(storage_ctx: StorageContext) -> CheckpointPort:
    return create_checkpoint(storage_ctx)


def _create_quarantine_from_settings(settings: Settings) -> QuarantinePort:
    return create_quarantine(cast("SettingsPort", settings))


@dataclass(frozen=True, slots=True)
class CommonServicePorts:
    """Resolved common ports required to assemble a ``PipelineService``."""

    storage_ctx: StorageContext
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics_port: MetricsPort
    tracer: TracingPort
    dq_services: DQServiceBundle


@dataclass(frozen=True, slots=True)
class CommonServicePortsRequest:
    """Inputs required to resolve the shared ports for one pipeline service."""

    settings: Settings
    logger: LoggerPort
    pipeline_config: PipelineYamlConfig
    pipeline_name: str
    create_dq_services_fn: Callable[
        [Settings, PipelineYamlConfig, LoggerPort, MetricsPort | None],
        DQServiceBundle,
    ]
    audit: AuditPort | None = None
    metrics: MetricsPort | None = None
    tracer: TracingPort | None = None
    metadata_coordinator: MetadataCoordinator | None = None
    silver_validator: SilverValidatorPort | None = None
    create_metrics_fn: Callable[[Settings], MetricsPort] = _create_metrics_from_settings
    storage_factory: type[_StorageFactoryProtocol] | None = None
    create_lock_fn: Callable[[], LockPort] = create_lock
    create_checkpoint_fn: Callable[[StorageContext], CheckpointPort] = (
        _create_checkpoint_for_storage
    )
    create_quarantine_fn: Callable[[Settings], QuarantinePort] = (
        _create_quarantine_from_settings
    )


def resolve_tracer(tracer: TracingPort | None) -> TracingPort:
    """Return the provided tracer or a NoOpTracing fallback."""
    return _resolve_tracing_port(tracer=tracer)


def build_common_service_ports(
    request: CommonServicePortsRequest,
) -> CommonServicePorts:
    """Create the reusable common ports shared by pipeline services."""
    metrics_port = (
        request.metrics
        if request.metrics is not None
        else request.create_metrics_fn(request.settings)
    )
    audit_port = request.audit if request.audit is not None else NoOpAudit()
    storage_factory = request.storage_factory
    if storage_factory is None:
        storage_factory = StorageFactory
    storage_ctx = storage_factory.create(
        request.settings,
        request.pipeline_config,
        request.logger,
        metrics=metrics_port,
        audit=audit_port,
        tracing=request.tracer,
        metadata_coordinator=request.metadata_coordinator,
        silver_validator=request.silver_validator,
        pipeline_name=request.pipeline_name,
    )
    return CommonServicePorts(
        storage_ctx=storage_ctx,
        lock=request.create_lock_fn(),
        checkpoint=request.create_checkpoint_fn(storage_ctx),
        quarantine=request.create_quarantine_fn(request.settings),
        metrics_port=metrics_port,
        tracer=resolve_tracer(request.tracer),
        dq_services=request.create_dq_services_fn(
            request.settings,
            request.pipeline_config,
            request.logger,
            metrics_port,
        ),
    )


def _coerce_dq_service_bundle(raw: object) -> DQServiceBundle:
    """Normalize DQServiceBundle or legacy mapping payloads."""
    if isinstance(raw, DQServiceBundle):
        return raw
    if isinstance(raw, Mapping):
        return DQServiceBundle(
            bronze_analyzer=raw.get("bronze_analyzer"),
            silver_analyzer=raw.get("silver_analyzer"),
            gold_analyzer=raw.get("gold_analyzer"),
            report_writer=raw.get("report_writer"),
            report_service=raw.get("report_service"),
        )
    return DQServiceBundle()


def assemble_pipeline_service(
    *,
    data_source: DataSourcePort,
    logger: LoggerPort,
    dq_monitor: DQMonitorPort | None,
    metadata_coordinator: MetadataCoordinator | None,
    common_ports: CommonServicePorts,
) -> PipelineService:
    """Assemble ``PipelineService`` from pre-built common ports."""
    from bioetl.application.core.wiring.runtime import PipelineService
    from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

    metadata_writer = MetadataWriter(logger=logger)
    dq_services = _coerce_dq_service_bundle(common_ports.dq_services)
    return PipelineService(
        data_source=data_source,
        storage=cast("PipelineStorageProtocol", common_ports.storage_ctx.adapter),  # pyright: ignore[reportInvalidCast]
        lock=common_ports.lock,
        checkpoint=common_ports.checkpoint,
        quarantine=common_ports.quarantine,
        metrics=common_ports.metrics_port,
        tracing=common_ports.tracer,
        logger=logger,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        metadata_writer=metadata_writer,
        bronze_dq_analyzer=cast("BronzeDQAnalyzerPort | None", dq_services.bronze_analyzer),
        silver_dq_analyzer=cast("SilverDQAnalyzerPort | None", dq_services.silver_analyzer),
        gold_dq_analyzer=cast("GoldDQAnalyzerPort | None", dq_services.gold_analyzer),
        dq_report_writer=cast("DQReportWriterPort | None", dq_services.report_writer),
        dq_report_service=cast("DQReportService | None", dq_services.report_service),
    )
