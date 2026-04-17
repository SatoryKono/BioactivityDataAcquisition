"""Internal wiring helpers for composite runner bootstrap assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.ports import LockPort
    from bioetl.infrastructure.config import Settings


@dataclass(frozen=True, slots=True)
class _BootstrapRuntimeBasics:
    """Resolved runtime-basics bundle used by bootstrap assembly."""

    run_id: str
    settings: Settings
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    storage: object
    lock: LockPort


@dataclass(frozen=True, slots=True)
class _BootstrapRunnerFactories:
    """Resolved phase runner factories used by composite bootstrap."""

    seed_factory: Callable[[], PipelineRunner]
    dependency_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    enricher_factory: Callable[[str, pl.DataFrame], PipelineRunner]


def _build_bootstrap_support_services(
    *,
    build_support_services_fn: Callable[..., CompositeSupportServices],
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    storage: object,
    run_id: str,
) -> CompositeSupportServices:
    """Build support services from the runtime basics payload."""
    return build_support_services_fn(
        config=config,
        runtime=runtime,
        settings=settings,
        logger=logger,
        storage=storage,
        run_id=run_id,
    )


def _resolve_bootstrap_runtime_basics(
    *,
    bootstrap_runtime_basics_fn: Callable[
        ...,
        tuple[str, Settings, LoggerPort, MetricsPort, TracingPort, object, LockPort],
    ],
    config: CompositeConfig,
    run_id: str | None,
) -> _BootstrapRuntimeBasics:
    """Resolve the named runtime-basics bundle for bootstrap assembly."""
    effective_run_id, settings, logger, metrics, tracer, storage, lock = (
        bootstrap_runtime_basics_fn(
            config=config,
            run_id=run_id,
        )
    )
    return _BootstrapRuntimeBasics(
        run_id=effective_run_id,
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        storage=storage,
        lock=lock,
    )


def _resolve_bootstrap_runner_factories(
    *,
    build_runner_factories_fn: Callable[
        ...,
        tuple[
            Callable[[], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
        ],
    ],
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
) -> _BootstrapRunnerFactories:
    """Resolve the named phase-factory bundle for composite bootstrap."""
    seed_factory, dependency_factory, enricher_factory = build_runner_factories_fn(
        config=config,
        runtime=runtime,
        logger=logger,
    )
    return _BootstrapRunnerFactories(
        seed_factory=seed_factory,
        dependency_factory=dependency_factory,
        enricher_factory=enricher_factory,
    )


def _create_bootstrapped_composite_runner(
    *,
    create_composite_runner_fn: Callable[..., CompositePipelineRunner],
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracer: TracingPort,
    lock: LockPort,
    seed_runner_factory: Callable[[], PipelineRunner],
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    support_services: CompositeSupportServices,
) -> CompositePipelineRunner:
    """Create the final runner from already-assembled bootstrap components."""
    return create_composite_runner_fn(
        config=config,
        runtime=runtime,
        run_id=run_id,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        lock=lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        support_services=support_services,
    )


def bootstrap_composite_runner_via_wiring(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
    bootstrap_runtime_basics_fn: Callable[
        ...,
        tuple[str, Settings, LoggerPort, MetricsPort, TracingPort, object, LockPort],
    ],
    build_runner_factories_fn: Callable[
        ...,
        tuple[
            Callable[[], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
        ],
    ],
    build_support_services_fn: Callable[..., CompositeSupportServices],
    create_composite_runner_fn: Callable[..., CompositePipelineRunner],
) -> CompositePipelineRunner:
    """Assemble and create composite runner with injected dependency builders."""
    runtime_basics = _resolve_bootstrap_runtime_basics(
        bootstrap_runtime_basics_fn=bootstrap_runtime_basics_fn,
        config=config,
        run_id=run_id,
    )
    runner_factories = _resolve_bootstrap_runner_factories(
        build_runner_factories_fn=build_runner_factories_fn,
        config=config,
        runtime=runtime,
        logger=runtime_basics.logger,
    )
    support_services = _build_bootstrap_support_services(
        build_support_services_fn=build_support_services_fn,
        config=config,
        runtime=runtime,
        settings=runtime_basics.settings,
        logger=runtime_basics.logger,
        storage=runtime_basics.storage,
        run_id=runtime_basics.run_id,
    )
    return _create_bootstrapped_composite_runner(
        create_composite_runner_fn=create_composite_runner_fn,
        config=config,
        runtime=runtime,
        run_id=runtime_basics.run_id,
        logger=runtime_basics.logger,
        metrics=runtime_basics.metrics,
        tracer=runtime_basics.tracer,
        lock=runtime_basics.lock,
        seed_runner_factory=runner_factories.seed_factory,
        dependencies_runner_factory=runner_factories.dependency_factory,
        enricher_runner_factory=runner_factories.enricher_factory,
        support_services=support_services,
    )
