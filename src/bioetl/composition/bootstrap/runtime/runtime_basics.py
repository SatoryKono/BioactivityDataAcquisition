"""Runtime dependency assembly helpers for composite bootstrap."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    CompositeCheckpointService,
    validate_join_key_normalization_policies,
)
from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    build_pipeline_context,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
        CompositeFilterExtractor,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
        CompositeSupportServicesFactory,
    )
    from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
        BronzeRunOptions,
        RunnerFactoryBuilder,
    )
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import (
        ClockPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.infrastructure.config.settings_api import Settings

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
    tracer_bootstrapper: Callable[[Settings], TracingPort],
    storage_bootstrapper: Callable[..., object],
    lock_factory: Callable[[], LockPort],
    uuid_factory: Callable[[], UUID],
    clock_factory: Callable[[], ClockPort] = SystemClock,
) -> CompositeInfrastructureContext:
    """Build base runtime dependencies shared across composite bootstrap.

    Args:
        config: CompositeConfig used to derive the pipeline name for logging.
        run_id: Optional UUID string; a new UUID is generated from uuid_factory
            when None.
        settings_provider: Zero-argument callable that returns global Settings.
        logger_bootstrapper: Callable accepting (pipeline_name, run_uuid, log_level)
            and returning a LoggerPort.
        storage_bootstrapper: Callable returning the composite runtime storage port; called with
            explicit ``RunContext`` and ports so storage assembly does not
            generate runtime identity.
        lock_factory: Zero-argument callable returning a LockPort.
        uuid_factory: Zero-argument callable returning a new UUID; injectable
            for deterministic testing.
        clock_factory: Zero-argument callable returning the runtime clock; injectable
            so tests and deterministic runners do not rely on wall-clock reads.

    Returns:
        CompositeInfrastructureContext with the typed runtime resource bundle for the composite run.
    """
    effective_run_id = run_id or str(uuid_factory())
    settings = settings_provider()
    logger = logger_bootstrapper(config.name, UUID(effective_run_id), "INFO")

    # Initialize domain layer enum fields with proper dependency injection
    from bioetl.composition.bootstrap.runtime.enum_loader_wiring import (
        initialize_domain_enum_fields,
    )

    initialize_domain_enum_fields()

    metrics = create_metrics(settings)
    tracer = tracer_bootstrapper(settings)
    clock = clock_factory()
    storage_run_context = RunContext(
        run_id=RunID(UUID(effective_run_id)),
        run_type=RunType.INCREMENTAL,
        started_at=clock.now(),
        pipeline_name=config.name,
        provider="composite",
        entity="merged",
    )
    storage = storage_bootstrapper(
        run_context=storage_run_context,
        logger=logger,
        metrics=metrics,
        tracing=tracer,
        enable_csv_export=True,
        settings=settings,
    )
    lock = lock_factory()
    return CompositeInfrastructureContext(
        run_id=effective_run_id,
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        storage=storage,
        lock=lock,
        clock=clock,
    )


def build_runner_factories(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
    runner_factory_builder_cls: type[RunnerFactoryBuilder[RunOptions]],
    filter_extraction_service_cls: type[CompositeFilterExtractor],
    pipeline_runner_builder: Callable[[PipelineRunContext], PipelineRunner],
    resolve_bronze_opts_fn: Callable[
        [CompositeRuntimeConfig, bool | None], BronzeRunOptions
    ],
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    """Build seed/dependency/enricher runner factories for composite phases.

    Args:
        config: CompositeConfig describing seed, enrichers, and dependencies.
        runtime: Runtime options used to resolve per-phase Bronze cache settings.
        logger: Structured logger forwarded to the runner factory builder.
        runner_factory_builder_cls: Class implementing per-phase runner factory
            construction.
        filter_extraction_service_cls: Class used to extract filter IDs from
            keys DataFrames during enricher/dependency factory invocations.
        pipeline_runner_builder: Callable that accepts a PipelineRunContext and
            returns a configured PipelineRunner.
        resolve_bronze_opts_fn: Callable returning BronzeRunOptions for a given
            runtime config and optional phase-level override flag.

    Returns:
        Tuple of (seed_factory, dependency_factory, enricher_factory) callables.
    """
    validate_join_key_normalization_policies(config)
    filter_extraction_service = filter_extraction_service_cls(
        logger=logger,
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
    )
    run_options_factory: Callable[..., RunOptions] = RunOptions
    build_context_fn: Callable[[str, RunOptions], PipelineRunContext] = (
        build_pipeline_context
    )
    runner_factory_builder = cast(
        "Callable[..., RunnerFactoryBuilder[RunOptions]]",
        runner_factory_builder_cls,
    )(
        logger=logger,
        run_options_cls=run_options_factory,
        build_context=build_context_fn,
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
    infra_context: CompositeInfrastructureContext,
    support_services_factory_cls: type[CompositeSupportServicesFactory],
    resolve_gold_schema_fn: Callable[[str], type | None],
    load_field_group_registry_fn: Callable[
        [str, LoggerPort], FieldGroupRegistry | None
    ],
    create_dq_report_service_fn: Callable[
        [LoggerPort, Settings, MetricsPort],
        DQReportService,
    ],
) -> CompositeSupportServices:
    """Build composite support service bundle consumed by runner facade.

    Args:
        config: CompositeConfig for this composite run.
        runtime: Runtime options (resume, concurrency, etc.).
        infra_context: Bundle of infrastructure primitives.
        support_services_factory_cls: Factory class that assembles the bundle.
        resolve_gold_schema_fn: Callable returning the Gold Pandera schema for
            a composite pipeline name, or None if not registered.
        load_field_group_registry_fn: Callable returning the FieldGroupRegistry
            for a composite pipeline name, or None.
        create_dq_report_service_fn: Callable returning a DQReportService
            given a logger and settings.

    Returns:
        CompositeSupportServices bundle with all services required by the runner.
    """
    return support_services_factory_cls(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        resolve_gold_schema=resolve_gold_schema_fn,
        load_field_group_registry=load_field_group_registry_fn,
        create_dq_report_service=create_dq_report_service_fn,
        checkpoint_manager_cls=CompositeCheckpointService,
    ).build()
