"""Internal wiring helpers for common pipeline service ports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.runtime import PipelineService
from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.services.port_factories import (
    create_checkpoint,
    create_lock,
    create_metrics,
    create_quarantine,
)
from bioetl.composition.factories.storage import StorageContext, StorageFactory
from bioetl.composition.observability_resolution import (
    resolve_tracing_port as _resolve_tracing_port,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CheckpointPort,
        DataSourcePort,
        DQMonitorPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class CommonServicePorts:
    """Resolved common ports required to assemble a ``PipelineService``."""

    storage_ctx: StorageContext
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics_port: MetricsPort
    tracer: TracingPort
    dq_services: JsonDict


@dataclass(frozen=True, slots=True)
class CommonServicePortsRequest:
    """Inputs required to resolve the shared ports for one pipeline service."""

    settings: Settings
    logger: LoggerPort
    pipeline_config: PipelineYamlConfig
    pipeline_name: str
    create_dq_services_fn: Callable[
        [Settings, PipelineYamlConfig, LoggerPort, MetricsPort | None],
        JsonDict,
    ]
    metrics: MetricsPort | None = None
    tracer: TracingPort | None = None
    metadata_coordinator: MetadataCoordinator | None = None
    silver_validator: SilverValidatorPort | None = None
    create_metrics_fn: Callable[[Settings], MetricsPort] = create_metrics
    storage_factory: type[StorageFactory] = StorageFactory
    create_lock_fn: Callable[[], LockPort] = create_lock
    create_checkpoint_fn: Callable[
        [StorageContext], CheckpointPort
    ] = create_checkpoint
    create_quarantine_fn: Callable[[Settings], QuarantinePort] = create_quarantine


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
    storage_ctx = request.storage_factory.create(
        request.settings,
        request.pipeline_config,
        request.logger,
        metrics=metrics_port,
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


def assemble_pipeline_service(
    *,
    data_source: DataSourcePort,
    logger: LoggerPort,
    dq_monitor: DQMonitorPort | None,
    metadata_coordinator: MetadataCoordinator | None,
    common_ports: CommonServicePorts,
) -> PipelineService:
    """Assemble ``PipelineService`` from pre-built common ports."""
    from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

    metadata_writer = MetadataWriter(logger=logger)
    return PipelineService(
        data_source=data_source,
        storage=common_ports.storage_ctx.adapter,
        lock=common_ports.lock,
        checkpoint=common_ports.checkpoint,
        quarantine=common_ports.quarantine,
        metrics=common_ports.metrics_port,
        tracing=common_ports.tracer,
        logger=logger,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        metadata_writer=metadata_writer,
        bronze_dq_analyzer=common_ports.dq_services.get("bronze_analyzer"),
        silver_dq_analyzer=common_ports.dq_services.get("silver_analyzer"),
        gold_dq_analyzer=common_ports.dq_services.get("gold_analyzer"),
        dq_report_writer=common_ports.dq_services.get("report_writer"),
        dq_report_service=common_ports.dq_services.get("report_service"),
    )
