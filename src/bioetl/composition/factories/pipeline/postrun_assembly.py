"""Postrun assembly helpers for pipeline factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.postrun.cleanup_orchestrator import (
    PostrunCleanupService,
)
from bioetl.application.core.postrun.compact_orchestrator import (
    PostrunCompactService,
)
from bioetl.application.core.postrun.dq_report_orchestrator import (
    PostrunDQReportService,
)
from bioetl.application.core.postrun.metadata_version_resolver import (
    PostrunMetadataVersionResolver,
)
from bioetl.application.core.postrun.service import (
    PostrunDependencyContext,
    PostrunService,
)
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.domain.exceptions import BioETLError

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
    )


_POSTRUN_WARNING_ALLOWLIST = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)
_METADATA_VERSION_ALLOWLIST = (
    ImportError,
    ModuleNotFoundError,
    FileNotFoundError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


def build_postrun_dependency_context(
    *,
    config: PipelineConfig,
    runtime: RuntimeConfig,
    storage: StorageMaintenancePort,
    logger_port: LoggerPort,
    dq_report_service: DQReportService | None = None,
    bronze_dq_config: BronzeDQConfigPort | None = None,
    silver_dq_config: SilverDQConfigPort | None = None,
    gold_dq_config: GoldDQConfigPort | None = None,
) -> PostrunDependencyContext:
    """Build the shared postrun collaborator graph for production and tests."""
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
        metadata_version_resolver=PostrunMetadataVersionResolver(
            logger=logger_port,
            runtime=runtime,
            warning_allowlist=_METADATA_VERSION_ALLOWLIST,
        ),
        compact_orchestrator=PostrunCompactService(
            config=config,
            storage=storage,
            logger=logger_port,
            warning_allowlist=_POSTRUN_WARNING_ALLOWLIST,
        ),
    )


def build_postrun_service(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
    lifecycle_service: MedallionLifecycleService,
    dq_configs: DQConfigsContext,
) -> PostrunService:
    """Build the postrun service and its collaborators in the composition layer."""
    dq_service = DataQualityService(
        dq_monitor=pipeline.services.dq_monitor,
        config=pipeline.config.dq,
        logger=logger_port,
        metrics=pipeline.services.metrics,
        pipeline_name=pipeline.config.pipeline_name,
        entity_type=pipeline.config.entity_type,
    )
    dependencies = build_postrun_dependency_context(
        config=pipeline.config,
        runtime=pipeline.runtime,
        storage=pipeline.services.storage,
        logger_port=logger_port,
        dq_report_service=pipeline.services.dq_report_service,
        bronze_dq_config=dq_configs.bronze,
        silver_dq_config=dq_configs.silver,
        gold_dq_config=dq_configs.gold,
    )
    return PostrunService(
        config=pipeline.config,
        runtime=pipeline.runtime,
        context=pipeline.context,
        dq_service=dq_service,
        lifecycle_service=lifecycle_service,
        storage=pipeline.services.storage,
        metrics=pipeline.services.metrics,
        logger=logger_port,
        dependencies=dependencies,
        metadata_coordinator=pipeline.services.metadata_coordinator,
        metadata_writer=pipeline.services.metadata_writer,
    )
