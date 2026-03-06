"""Runtime dependency assembly helpers for composite bootstrap."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.application.composite.checkpoint import CompositeCheckpointService

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runner import CompositeRuntimeConfig
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
        CompositeFilterExtractionService,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
        CompositeSupportServicesFactory,
    )
    from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
        BronzeRunOptions,
        RunnerFactoryBuilderService,
    )
    from bioetl.composition.entrypoints import RunOptions
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import LockPort, LoggerPort
    from bioetl.infrastructure.config import Settings


__all__ = [
    "bootstrap_runtime_basics",
    "build_runner_factories",
    "build_support_services",
]


def bootstrap_runtime_basics(
    *,
    config: CompositeConfig,
    run_id: str | None,
    settings_provider: Callable[[], Settings],
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort],
    storage_bootstrapper: Callable[..., object],
    lock_factory: Callable[[], LockPort],
    uuid_factory: Callable[[], UUID],
) -> tuple[str, Settings, LoggerPort, object, LockPort]:
    """Build base runtime dependencies shared across composite bootstrap."""
    effective_run_id = run_id or str(uuid_factory())
    settings = settings_provider()
    logger = logger_bootstrapper(config.name, UUID(effective_run_id), "INFO")
    storage = storage_bootstrapper(enable_csv_export=True)
    lock = lock_factory()
    return effective_run_id, settings, logger, storage, lock


def build_runner_factories(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
    runner_factory_builder_cls: type[RunnerFactoryBuilderService[RunOptions]],
    filter_extraction_service_cls: type[CompositeFilterExtractionService],
    pipeline_runner_builder: Callable[[PipelineRunContext], PipelineRunner],
    resolve_bronze_opts_fn: Callable[
        [CompositeRuntimeConfig, bool | None], BronzeRunOptions
    ],
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    """Build seed/dependency/enricher runner factories for composite phases."""
    # CIRCULAR-DEPENDENCY: kept local to avoid entrypoints bootstrap cycle.
    from bioetl.composition.entrypoints import RunOptions, build_pipeline_context

    filter_extraction_service = filter_extraction_service_cls(logger=logger)
    runner_factory_builder = runner_factory_builder_cls(
        logger=logger,
        run_options_cls=RunOptions,
        build_context=build_pipeline_context,
        pipeline_runner_builder=pipeline_runner_builder,
        filter_extraction_service=filter_extraction_service,
    )
    seed_factory = runner_factory_builder.build_seed_factory(
        seed_pipeline=config.seed.pipeline,
        seed_limit=runtime.seed_limit,
        bronze_opts=resolve_bronze_opts_fn(runtime, None),
    )
    enricher_factory = runner_factory_builder.build_enricher_factory(
        enrichers=list(config.enrichers),
        bronze_opts=resolve_bronze_opts_fn(
            runtime,
            runtime.cached_bronze_enrichers,
        ),
    )
    dependency_factory = runner_factory_builder.build_dependency_factory(
        dependencies=list(config.dependencies),
        bronze_opts=resolve_bronze_opts_fn(
            runtime,
            runtime.cached_bronze_dependencies,
        ),
    )
    return seed_factory, dependency_factory, enricher_factory


def build_support_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    storage: object,
    run_id: str,
    support_services_factory_cls: type[CompositeSupportServicesFactory],
    resolve_gold_schema_fn: Callable[[str], type | None],
    load_field_group_registry_fn: Callable[
        [str, LoggerPort], FieldGroupRegistry | None
    ],
    create_dq_report_service_fn: Callable[[LoggerPort, Settings], DQReportService],
) -> CompositeSupportServices:
    """Build composite support service bundle consumed by runner facade."""
    return support_services_factory_cls(
        config=config,
        runtime=runtime,
        settings=settings,
        logger=logger,
        storage=storage,
        run_id=run_id,
        resolve_gold_schema=resolve_gold_schema_fn,
        load_field_group_registry=load_field_group_registry_fn,
        create_dq_report_service=create_dq_report_service_fn,
        checkpoint_manager_cls=CompositeCheckpointService,
    ).build()
