"""Runtime dependency assembly helpers for composite bootstrap."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from bioetl.composition.bootstrap.runtime.composite_replay_inputs import (
    load_runtime_composite_replay,
)

from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    validate_join_key_normalization_policies,
)
from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime._dependency_runner_support import (
    resolve_required_gold_pipelines,
)
from bioetl.composition.bootstrap.runtime.composite_child_runner import (
    build_reported_child_runner,
)
from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
    build_support_services,
)
from bioetl.composition.bootstrap.runtime.enum_loader_wiring import (
    initialize_domain_enum_fields,
)
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    build_pipeline_context,
)
from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
    RunnerFactoryHooks,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.domain.ports import ExecutionMetricsRunnerPort as PipelineRunner
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeRuntimeStorageProtocol,
    )
    from bioetl.application.composite.helpers.filter_extraction import (
        CompositeFilterExtractor,
    )
    from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
        BronzeRunOptions,
        RunnerFactoryBuilder,
    )
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import (
        ClockPort,
        LockPort,
        LoggerPort,
        PipelineControlPlaneArtifacts,
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
    storage_bootstrapper: Callable[..., CompositeRuntimeStorageProtocol],
    lock_factory: Callable[[], LockPort],
    uuid_factory: Callable[[], UUID],
    clock_factory: Callable[[], ClockPort] = SystemClock,
) -> CompositeInfrastructureContext:
    """Build base runtime dependencies shared across composite bootstrap.

    Storage receives an explicit ``RunContext`` so assembly does not generate a
    second runtime identity.
    """
    effective_run_id = run_id or str(uuid_factory())
    settings = settings_provider()
    logger = logger_bootstrapper(config.name, UUID(effective_run_id), "INFO")

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

    def storage_for_manifest(
        artifacts: PipelineControlPlaneArtifacts,
    ) -> CompositeRuntimeStorageProtocol:
        bound_context = replace(
            storage_run_context,
            manifest_id=artifacts.manifest_id,
            config_hash=artifacts.config_hash,
            resolved_config_hash=artifacts.resolved_config_hash,
            effective_config_hash=artifacts.effective_config_hash,
            execution_fingerprint=artifacts.execution_fingerprint,
            dq_contract_compatibility_hash=artifacts.dq_contract_compatibility_hash,
            effective_config_artifact_id=artifacts.effective_config_artifact_id,
            input_snapshot_fingerprint=artifacts.input_snapshot_fingerprint,
        )
        return storage_bootstrapper(
            run_context=bound_context,
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
        storage_for_manifest=storage_for_manifest,
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
    """Build phase factories with normalized filters and verified child reports.

    Injected builders own context, pipeline execution, and Bronze option policy.
    Replay options are prepared before context creation; saved manifests are
    checked before wrapping each child runner with its report writer.
    """
    validate_join_key_normalization_policies(config)
    filter_extraction_service = filter_extraction_service_cls(
        logger=logger,
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
    )
    run_options_factory: Callable[..., RunOptions] = RunOptions
    replay = load_runtime_composite_replay(config, runtime)

    def build_context_fn(name: str, options: RunOptions) -> PipelineRunContext:
        # Composite phases require an explicit clock, like entity runners.
        return build_pipeline_context(
            name,
            options,
            clock=SystemClock(),
            run_id_factory=uuid4 if options.exact_replay else None,
        )

    def build_verified_runner(context: PipelineRunContext) -> PipelineRunner:
        runner = pipeline_runner_builder(context)
        if replay is not None:
            replay.validate_runtime_manifest(context.pipeline_name, context.run_id)
        return runner

    runner_factory_builder = cast(
        "Callable[..., RunnerFactoryBuilder[RunOptions]]",
        runner_factory_builder_cls,
    )(
        logger=logger,
        run_options_cls=run_options_factory,
        build_context=build_context_fn,
        pipeline_runner_builder=build_verified_runner,
        hooks=RunnerFactoryHooks(
            replay_options=replay.prepare_options if replay is not None else None,
            reporting_runner_builder=lambda context, options: (
                build_reported_child_runner(
                    context=context,
                    options=options,
                    runner_builder=build_verified_runner,
                )
            ),
        ),
        filter_extraction_service=filter_extraction_service,
        gold_required_pipelines=resolve_required_gold_pipelines(config),
        required_persistence_profile=getattr(
            runtime, "required_persistence_profile", None
        ),
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
