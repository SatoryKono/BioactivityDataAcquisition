"""Postrun assembly helpers for pipeline factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.postrun import (
    PostrunCleanupService,
    PostrunCompactService,
    PostrunDependencyContext,
    PostrunDQReportService,
    PostrunMetadataVersionResolver,
    PostrunMetadataWriteService,
    PostrunService,
)
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.services.common_service_wiring import resolve_tracer
from bioetl.domain.context import PipelineContext
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import MetadataCoordinatorPort, MetadataWriterPort
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        SilverDQConfigPort,
        StorageMaintenancePort,
        TracingPort,
    )


_POSTRUN_WARNING_ALLOWLIST = (
    BioETLError,
    OSError,
    RuntimeError,
    TimeoutError,
    ValueError,
)
_METADATA_VERSION_ALLOWLIST = (
    FileNotFoundError,
    OSError,
    RuntimeError,
    ValueError,
)


def build_postrun_dependency_context(
    *,
    config: PipelineConfig,
    runtime: RuntimeConfig,
    context: PipelineContext,
    storage: StorageMaintenancePort,
    logger_port: LoggerPort,
    dq_report_service: DQReportService | None = None,
    bronze_dq_config: BronzeDQConfigPort | None = None,
    silver_dq_config: SilverDQConfigPort | None = None,
    gold_dq_config: GoldDQConfigPort | None = None,
    metadata_coordinator: MetadataCoordinatorPort | None = None,
    metadata_writer: MetadataWriterPort | None = None,
) -> PostrunDependencyContext:
    """Build the shared postrun collaborator graph for production and tests."""
    metadata_version_resolver = PostrunMetadataVersionResolver(
        logger=logger_port,
        runtime=runtime,
        storage=storage,
        warning_allowlist=_METADATA_VERSION_ALLOWLIST,
    )
    return PostrunDependencyContext(
        cleanup_orchestrator=PostrunCleanupService(
            logger=logger_port,
            warning_allowlist=_POSTRUN_WARNING_ALLOWLIST,
        ),
        dq_report_orchestrator=PostrunDQReportService(
            logger=logger_port,
            runtime=runtime,
            dq_report_service=dq_report_service,
            bronze_dq_config=bronze_dq_config,
            silver_dq_config=silver_dq_config,
            gold_dq_config=gold_dq_config,
            warning_allowlist=_POSTRUN_WARNING_ALLOWLIST,
        ),
        metadata_write_orchestrator=PostrunMetadataWriteService(
            config=config,
            runtime=runtime,
            context=context,
            storage=storage,
            metadata_coordinator=metadata_coordinator,
            metadata_writer=metadata_writer,
            metadata_version_resolver=metadata_version_resolver,
            clock=SystemClock(),
        ),
        compact_orchestrator=PostrunCompactService(
            config=config,
            storage=storage,
            logger=logger_port,
            warning_allowlist=_POSTRUN_WARNING_ALLOWLIST,
        ),
    )


def _build_pipeline_dq_service(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> DataQualityService:
    """Build the pipeline-scoped DataQualityService from outer wiring."""
    return DataQualityService(
        dq_monitor=pipeline.services.dq_monitor,
        config=pipeline.config.dq,
        logger=logger_port,
        metrics=pipeline.services.metrics,
        pipeline_name=pipeline.config.pipeline_name,
        entity_type=pipeline.config.entity_type,
        run_type=pipeline.runtime.run_type.value,
    )


def _build_pipeline_postrun_dependencies(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
    dq_configs: DQConfigsContext,
) -> PostrunDependencyContext:
    """Build postrun dependencies from pipeline services and DQ config seams."""
    return build_postrun_dependency_context(
        config=pipeline.config,
        runtime=pipeline.runtime,
        context=pipeline.context,
        storage=pipeline.services.storage,
        logger_port=logger_port,
        dq_report_service=pipeline.services.dq_report_service,
        bronze_dq_config=dq_configs.bronze,
        silver_dq_config=dq_configs.silver,
        gold_dq_config=dq_configs.gold,
        metadata_coordinator=pipeline.services.metadata_coordinator,
        metadata_writer=pipeline.services.metadata_writer,
    )


def build_postrun_service(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
    lifecycle_service: MedallionLifecycleService,
    dq_configs: DQConfigsContext,
    tracer: TracingPort | None = None,
) -> PostrunService:
    """Build the postrun service and its collaborators in the composition layer."""
    resolved_tracer = resolve_tracer(tracer)
    dq_service = _build_pipeline_dq_service(
        pipeline=pipeline,
        logger_port=logger_port,
    )
    dependencies = _build_pipeline_postrun_dependencies(
        pipeline=pipeline,
        logger_port=logger_port,
        dq_configs=dq_configs,
    )
    return PostrunService(
        config=pipeline.config,
        runtime=pipeline.runtime,
        context=pipeline.context,
        dq_service=dq_service,
        lifecycle_service=lifecycle_service,
        dependencies=dependencies,
        tracer=resolved_tracer,
        storage=pipeline.services.storage,
        metrics=pipeline.services.metrics,
        logger=logger_port,
    )
