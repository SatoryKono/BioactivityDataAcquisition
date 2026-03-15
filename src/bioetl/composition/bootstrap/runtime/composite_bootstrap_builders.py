"""Internal builder helpers for composite runtime bootstrap.

This module holds orchestration internals so ``composite.py`` can remain
as a thin compatibility facade with stable patch points.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime.runner_assembly import (
    create_composite_runner as _create_composite_runner_impl,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    bootstrap_runtime_basics as _bootstrap_runtime_basics_impl,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    build_runner_factories as _build_runner_factories_impl,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    build_support_services as _build_support_services_impl,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    import polars as pl

    from bioetl.application.composite.runner_pkg import CompositePipelineRunnerService
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
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
    "create_composite_runner",
]


@dataclass(frozen=True, slots=True)
class CompositeRuntimeBasics:
    """Named runtime-basics handoff used by the composite bootstrap facade."""

    run_id: str
    settings: Settings
    logger: LoggerPort
    storage: object
    lock: LockPort


def bootstrap_runtime_basics(
    *,
    config: CompositeConfig,
    run_id: str | None,
    settings_provider: Callable[[], Settings],
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort],
    storage_bootstrapper: Callable[..., object],
    lock_factory: Callable[[], LockPort],
    uuid_factory: Callable[[], UUID],
 ) -> CompositeRuntimeBasics:
    """Build base runtime dependencies shared across composite bootstrap.

    Args:
        config: Validated CompositeConfig used to derive the pipeline name.
        run_id: Optional run UUID string; a new UUID is generated when None.
        settings_provider: Callable returning global Settings.
        logger_bootstrapper: Callable accepting (pipeline_name, run_uuid, log_level)
            and returning a LoggerPort.
        storage_bootstrapper: Callable returning a storage adapter (any type).
        lock_factory: Callable returning a LockPort implementation.
        uuid_factory: Callable returning a new UUID (injectable for testing).

    Returns:
        Named runtime-basics handoff for the composite run.
    """
    run_id_value, settings, logger, storage, lock = _bootstrap_runtime_basics_impl(
        config=config,
        run_id=run_id,
        settings_provider=settings_provider,
        logger_bootstrapper=logger_bootstrapper,
        storage_bootstrapper=storage_bootstrapper,
        lock_factory=lock_factory,
        uuid_factory=uuid_factory,
    )
    return CompositeRuntimeBasics(
        run_id=run_id_value,
        settings=settings,
        logger=logger,
        storage=storage,
        lock=lock,
    )


def build_runner_factories(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
    runner_factory_builder_cls: type[RunnerFactoryBuilderService[RunOptions]],
    filter_extraction_service_cls: type[CompositeFilterExtractionService],
    pipeline_runner_builder: Callable[[PipelineRunContext], PipelineRunner],
    resolve_bronze_opts_fn: Callable[
        [CompositeRuntimeConfig, bool | None],
        BronzeRunOptions,
    ],
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    """Build seed/dependency/enricher runner factories for composite phases.

    Args:
        config: CompositeConfig describing seed, enrichers, and dependencies.
        runtime: Runtime options used to resolve Bronze cache settings per phase.
        logger: Structured logger forwarded to filter extraction and runner builder.
        runner_factory_builder_cls: Class used to build per-phase runner factories.
        filter_extraction_service_cls: Class used to extract filter IDs from keys DataFrames.
        pipeline_runner_builder: Callable that accepts a PipelineRunContext and
            returns a configured PipelineRunner.
        resolve_bronze_opts_fn: Callable to resolve per-phase cached Bronze options.

    Returns:
        Tuple of (seed_factory, dependency_factory, enricher_factory) callables.
    """
    return _build_runner_factories_impl(
        config=config,
        runtime=runtime,
        logger=logger,
        runner_factory_builder_cls=runner_factory_builder_cls,
        filter_extraction_service_cls=filter_extraction_service_cls,
        pipeline_runner_builder=pipeline_runner_builder,
        resolve_bronze_opts_fn=resolve_bronze_opts_fn,
    )


def build_support_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    runtime_basics: CompositeRuntimeBasics,
    support_services_factory_cls: type[CompositeSupportServicesFactory],
    resolve_gold_schema_fn: Callable[[str], type | None],
    load_field_group_registry_fn: Callable[
        [str, LoggerPort], FieldGroupRegistry | None
    ],
    create_dq_report_service_fn: Callable[[LoggerPort, Settings], DQReportService],
) -> CompositeSupportServices:
    """Build composite support service bundle consumed by runner facade.

    Args:
        config: CompositeConfig for this composite run.
        runtime: Runtime options (resume, concurrency, etc.).
        runtime_basics: Named runtime-basics handoff containing settings, logger,
            storage, and run_id for this bootstrap cycle.
        support_services_factory_cls: Factory class used to build the bundle.
        resolve_gold_schema_fn: Callable returning the Gold Pandera schema for
            a composite pipeline name, or None.
        load_field_group_registry_fn: Callable returning the FieldGroupRegistry
            for a composite pipeline name, or None.
        create_dq_report_service_fn: Callable returning a DQReportService.

    Returns:
        CompositeSupportServices bundle with all services required by the runner.
    """
    return _build_support_services_impl(
        config=config,
        runtime=runtime,
        settings=runtime_basics.settings,
        logger=runtime_basics.logger,
        storage=runtime_basics.storage,
        run_id=runtime_basics.run_id,
        support_services_factory_cls=support_services_factory_cls,
        resolve_gold_schema_fn=resolve_gold_schema_fn,
        load_field_group_registry_fn=load_field_group_registry_fn,
        create_dq_report_service_fn=create_dq_report_service_fn,
    )


def create_composite_runner(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str,
    logger: LoggerPort,
    lock: LockPort,
    seed_runner_factory: Callable[[], PipelineRunner],
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    support_services: CompositeSupportServices,
    runner_factory: Callable[..., CompositePipelineRunnerService],
) -> CompositePipelineRunnerService:
    """Create fully wired CompositePipelineRunner service.

    Args:
        config: CompositeConfig for this composite run.
        runtime: Runtime options for the composite run.
        run_id: UUID string identifying this run.
        logger: Structured logger forwarded to the runner.
        lock: LockPort used for distributed execution safety.
        seed_runner_factory: Callable that creates a seed-phase PipelineRunner.
        dependencies_runner_factory: Callable that creates a dependency-phase
            PipelineRunner given a pipeline name and keys DataFrame.
        enricher_runner_factory: Callable that creates an enricher-phase
            PipelineRunner given a pipeline name and keys DataFrame.
        support_services: Bundle of support services (checkpoint, merger, etc.).
        runner_factory: Factory callable used to instantiate
            CompositePipelineRunnerService with all wired dependencies.

    Returns:
        Fully wired CompositePipelineRunnerService ready for execution.
    """
    return _create_composite_runner_impl(
        config=config,
        runtime=runtime,
        run_id=run_id,
        logger=logger,
        lock=lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        support_services=support_services,
        runner_factory=runner_factory,
    )
