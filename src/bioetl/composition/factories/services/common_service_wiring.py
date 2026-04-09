"""Internal wiring helpers for common pipeline service ports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.runtime_wiring_api import PipelineService
from bioetl.application.services.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.services.port_factories import (
    create_checkpoint,
    create_lock,
    create_metrics,
    create_quarantine,
)
from bioetl.composition.factories.storage import StorageContext, StorageFactory
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


def resolve_tracer(tracer: TracingPort | None) -> TracingPort:
    """Return the provided tracer or a NoOpTracing fallback."""
    if tracer is None:
        from bioetl.domain.ports.noop import NoOpTracing

        return NoOpTracing()
    return tracer


def build_common_service_ports(
    *,
    settings: Settings,
    logger: LoggerPort,
    pipeline_config: PipelineYamlConfig,
    metrics: MetricsPort | None = None,
    tracer: TracingPort | None = None,
    metadata_coordinator: MetadataCoordinator | None = None,
    silver_validator: SilverValidatorPort | None = None,
    create_dq_services_fn: Callable[
        [Settings, PipelineYamlConfig, LoggerPort, MetricsPort | None],
        JsonDict,
    ],
    create_metrics_fn: Callable[[Settings], MetricsPort] = create_metrics,
    storage_factory: type[StorageFactory] = StorageFactory,
    create_lock_fn: Callable[[], LockPort] = create_lock,
    create_checkpoint_fn: Callable[
        [StorageContext], CheckpointPort
    ] = create_checkpoint,
    create_quarantine_fn: Callable[[Settings], QuarantinePort] = create_quarantine,
) -> CommonServicePorts:
    """Create the reusable common ports shared by pipeline services."""
    metrics_port = metrics if metrics is not None else create_metrics_fn(settings)
    storage_ctx = storage_factory.create(
        settings,
        pipeline_config,
        logger,
        metrics=metrics_port,
        metadata_coordinator=metadata_coordinator,
        silver_validator=silver_validator,
    )
    return CommonServicePorts(
        storage_ctx=storage_ctx,
        lock=create_lock_fn(),
        checkpoint=create_checkpoint_fn(storage_ctx),
        quarantine=create_quarantine_fn(settings),
        metrics_port=metrics_port,
        tracer=resolve_tracer(tracer),
        dq_services=create_dq_services_fn(
            settings,
            pipeline_config,
            logger,
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
