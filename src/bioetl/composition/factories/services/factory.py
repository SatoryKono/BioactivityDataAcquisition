"""Services factory façade for pipeline service wiring."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.factory import PipelineService
from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.dq.context_resolver import (
    create_dq_services as _create_dq_services_impl,
)
from bioetl.composition.factories.dq.context_resolver import (
    get_flat_structure as _get_flat_structure_impl,
)
from bioetl.composition.factories.dq.context_resolver import (
    get_output_root as _get_output_root_impl,
)
from bioetl.composition.factories.dq.context_resolver import (
    is_dq_report_enabled as _is_dq_report_enabled_impl,
)
from bioetl.composition.factories.dq.factory import DQServicesFactory
from bioetl.composition.factories.services.builder import ServicesBuilder
from bioetl.composition.factories.services.callbacks import (
    create_data_normalization_service,
    extract_pipeline_callbacks,
)
from bioetl.composition.factories.services.common_service_wiring import (
    CommonServicePorts,
    CommonServicePortsRequest,
    assemble_pipeline_service,
    build_common_service_ports,
    resolve_tracer,
)
from bioetl.composition.factories.services.port_factories import (
    create_checkpoint,
    create_lock,
    create_metrics,
    create_quarantine,
)
from bioetl.composition.factories.storage import StorageFactory
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.composition.factories.storage import StorageContext
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

__all__ = [
    "BaseServicesFactory",
    "DQServicesFactory",
    "ServicesBuilder",
    "create_data_normalization_service",
    "extract_pipeline_callbacks",
]


class BaseServicesFactory:
    """Reusable factory for common services (local deployment)."""

    @staticmethod
    def _create_metrics(settings: Settings) -> MetricsPort:
        """Compatibility wrapper delegating metrics creation to port factories."""
        return create_metrics(settings)

    @classmethod
    def create_common_services(
        cls,
        settings: Settings,
        logger: LoggerPort,
        data_source: DataSourcePort,
        pipeline_config: PipelineYamlConfig,
        pipeline_name: str,
        metrics: MetricsPort | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
    ) -> PipelineService:
        """Create a fully wired `PipelineService` bundle for one pipeline run."""
        cls._ensure_prod_silver_validator(settings, pipeline_config, silver_validator)
        common_ports = build_common_service_ports(
            CommonServicePortsRequest(
                settings=settings,
                logger=logger,
                pipeline_config=pipeline_config,
                pipeline_name=pipeline_name,
                metrics=metrics,
                tracer=tracer,
                metadata_coordinator=metadata_coordinator,
                silver_validator=silver_validator,
                create_dq_services_fn=cls._create_dq_services,
                create_metrics_fn=create_metrics,
                storage_factory=StorageFactory,
                create_lock_fn=create_lock,
                create_checkpoint_fn=create_checkpoint,
                create_quarantine_fn=create_quarantine,
            )
        )
        return assemble_pipeline_service(
            data_source=data_source,
            logger=logger,
            dq_monitor=dq_monitor,
            metadata_coordinator=metadata_coordinator,
            common_ports=common_ports,
        )

    @staticmethod
    def _ensure_prod_silver_validator(
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        silver_validator: SilverValidatorPort | None,
    ) -> None:
        """Enforce validator requirement in production mode."""
        if (
            settings.env == "prod"
            and not settings.test_mode
            and silver_validator is None
        ):
            raise ValueError(
                "Silver validator is required for production pipelines "
                f"(pipeline={pipeline_config.pipeline_name})"
            )

    @staticmethod
    def _resolve_tracer(tracer: TracingPort | None) -> TracingPort:
        """Return tracer or fallback to NoOpTracing."""
        return resolve_tracer(tracer)

    @staticmethod
    def _build_pipeline_services(
        *,
        data_source: DataSourcePort,
        storage_ctx: StorageContext,
        lock: LockPort,
        checkpoint: CheckpointPort,
        quarantine: QuarantinePort,
        metrics_port: MetricsPort,
        tracer: TracingPort,
        logger: LoggerPort,
        dq_monitor: DQMonitorPort | None,
        metadata_coordinator: MetadataCoordinator | None,
        dq_services: JsonDict,  # Any: heterogeneous DQ service instances
    ) -> PipelineService:
        """Assemble PipelineService from pre-built dependencies."""
        return assemble_pipeline_service(
            data_source=data_source,
            logger=logger,
            dq_monitor=dq_monitor,
            metadata_coordinator=metadata_coordinator,
            common_ports=CommonServicePorts(
                storage_ctx=storage_ctx,
                lock=lock,
                checkpoint=checkpoint,
                quarantine=quarantine,
                metrics_port=metrics_port,
                tracer=tracer,
                dq_services=dq_services,
            ),
        )

    @staticmethod
    def _get_output_root(
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> Path:
        """Derive output root from pipeline config or fall back to settings."""
        return _get_output_root_impl(settings, pipeline_config)

    @classmethod
    def _create_dq_services(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
    ) -> JsonDict:  # Any: heterogeneous DQ service instances
        """Create DQ analyzers/writer/services when DQ reporting is enabled."""
        return _create_dq_services_impl(
            settings,
            pipeline_config,
            logger,
            metrics,
        )

    @staticmethod
    def _is_dq_report_enabled(config: PipelineYamlConfig) -> bool:
        """Check if any DQ report is enabled in pipeline config."""
        return _is_dq_report_enabled_impl(config)

    @staticmethod
    def _get_flat_structure(config: PipelineYamlConfig) -> bool:
        """Get flat_structure setting from pipeline config."""
        return _get_flat_structure_impl(config)
