"""Helper factories for composite runtime support services."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.config.field_group_loader import (
    FieldGroupLoadError,
    load_field_groups,
)

from bioetl.application.services.quality.dq_report_service import DQReportService
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    bootstrap_runtime_basics as _bootstrap_runtime_basics_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    build_runner_factories as _build_runner_factories_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    build_support_services as _build_support_services_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
    CompositeFilterExtractor,
)
from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
    CompositeSupportServicesFactory,
)
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_logger,
    bootstrap_tracer,
)
from bioetl.composition.bootstrap.runtime.pipeline import (
    bootstrap_pipeline_runner as bootstrap_pipeline_runner_impl,
)
from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
    RunnerFactoryBuilder,
    resolve_bronze_opts,
)
from bioetl.composition.occurrence_identity import create_runtime_occurrence_uuid
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
from bioetl.infrastructure.locking.memory_lock import MemoryLock

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.config.settings_api import Settings

FIELD_GROUP_CONFIG_DIR = Path("configs/composites/field_groups")


def _composite_basics_uuid_factory() -> str:
    """Factory function for composite basics UUID generation."""

    return str(create_runtime_occurrence_uuid("composite_basics"))


def bootstrap_runtime_basics_facade(
    *,
    config: CompositeConfig,
    run_id: str | None,
    bootstrap_runtime_basics_impl: Callable[..., CompositeInfrastructureContext],
) -> CompositeInfrastructureContext:
    """Build base runtime dependencies shared across composite bootstrap."""
    from uuid import UUID

    def _bootstrap_logger(
        pipeline_name: str,
        run_uuid: UUID,
        level: str,
    ) -> object:
        return bootstrap_logger(
            pipeline=pipeline_name,
            run_id=run_uuid,
            log_level=level,
        )

    return bootstrap_runtime_basics_impl(
        config=config,
        run_id=run_id,
        bootstrap_runtime_basics_builder_fn=_bootstrap_runtime_basics_builder_impl,
        settings_provider=get_settings,
        logger_bootstrapper=_bootstrap_logger,
        tracer_bootstrapper=bootstrap_tracer,
        storage_bootstrapper=bootstrap_storage_adapter,
        lock_factory=MemoryLock,
        uuid_factory=_composite_basics_uuid_factory,
    )


def build_runner_factories_facade(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
    build_runner_factories_impl: Callable[
        ...,
        tuple[
            Callable[[], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
        ],
    ],
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    """Build seed/dependency/enricher runner factories for composite phases."""

    return build_runner_factories_impl(
        config=config,
        runtime=runtime,
        logger=logger,
        build_runner_factories_builder_fn=_build_runner_factories_builder_impl,
        runner_factory_builder_cls=RunnerFactoryBuilder,
        filter_extraction_service_cls=CompositeFilterExtractor,
        pipeline_runner_builder=bootstrap_pipeline_runner_impl,
        resolve_bronze_opts_fn=resolve_bronze_opts,
    )


def build_support_services_facade(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    build_support_services_impl: Callable[..., CompositeSupportServices],
    resolve_gold_schema_fn: Callable[..., object],
    load_field_group_registry_fn: Callable[..., object],
) -> CompositeSupportServices:
    """Build composite support service bundle consumed by runner facade."""

    return build_support_services_impl(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        build_support_services_builder_fn=_build_support_services_builder_impl,
        support_services_factory_cls=CompositeSupportServicesFactory,
        resolve_gold_schema_fn=resolve_gold_schema_fn,
        load_field_group_registry_fn=load_field_group_registry_fn,
        create_dq_report_service_fn=_create_dq_report_service,
    )


def _load_field_group_registry(
    composite_name: str,
    logger: LoggerPort,
) -> FieldGroupRegistry | None:
    """Load field group registry for composite pipeline if config exists.

    Resolves the entity name from the composite pipeline name, looks for a
    YAML config file in the canonical field groups directory, and loads the
    registry. Returns None silently when no config is found so callers can
    treat missing field group configs as an opt-out.

    Args:
        composite_name: Composite pipeline name (e.g., 'composite_publication').
        logger: Structured logger used to emit debug/info/warning events.

    Returns:
        Populated FieldGroupRegistry if a config file exists, None otherwise.
    """
    entity = (
        composite_name.replace("composite_", "")
        if "_" in composite_name
        else composite_name
    )
    config_path = FIELD_GROUP_CONFIG_DIR / f"{entity}.yaml"
    if not config_path.exists():
        logger.debug(
            "No field group config found, skipping",
            config_path=str(config_path),
        )
        return None

    try:
        registry = load_field_groups(config_path)
        logger.info(
            "Loaded field group registry",
            config_path=str(config_path),
            groups=len(registry.groups),
            fields=registry.field_count,
            columns=registry.column_count,
        )
        return registry
    except (FieldGroupLoadError, FileNotFoundError) as error:
        logger.warning(
            "Failed to load field group config, continuing without it",
            error=str(error),
            config_path=str(config_path),
        )
        return None


def _create_dq_report_service(
    logger: LoggerPort,
    settings: Settings,
    metrics: MetricsPort,
) -> DQReportService:
    """Create DQ report service for composite pipelines.

    Builds a DQReportService wired with a DQReportWriter that writes reports
    to the canonical DQ output path under data_dir.

    Args:
        logger: Structured logger forwarded to both the writer and service.
        settings: Global settings providing data_dir for report output paths.
        metrics: Metrics port used for DQ lifecycle counters.

    Returns:
        DQReportService ready for composite pipeline DQ report generation.
    """

    reports_base_path = Path(settings.data_dir) / "output" / "reports" / "dq"
    report_writer = DQReportWriter(
        base_path=reports_base_path,
        logger=logger,
    )
    return DQReportService(
        logger=logger,
        report_writer=report_writer,
        metrics=metrics,
    )
