"""Shared runtime-resource helpers for composite bootstrap planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypeGuard

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.composite.runner_pkg import CompositePipelineRunner
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.composition.bootstrap.runtime._composite_plan_support import (
        CompositeBootstrapPlan,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import (
        ClockPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.infrastructure.config.settings_api import Settings


@dataclass(frozen=True, slots=True)
class BootstrapRuntimeResources:
    """Resolved runtime-basics bundle shared by bootstrap orchestration."""

    run_id: str
    settings: Settings
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    storage: object
    lock: LockPort
    clock: ClockPort | None = None
    infra_context: object | None = None


class _NamedRuntimeBundle(Protocol):
    run_id: str
    settings: Settings
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    storage: object
    lock: LockPort


def build_bootstrap_runtime_resources(
    *,
    bootstrap_runtime_basics_fn: Callable[..., object],
    config: CompositeConfig,
    run_id: str | None,
) -> BootstrapRuntimeResources:
    """Resolve the canonical runtime-basics resource bundle."""
    resolved_bundle = bootstrap_runtime_basics_fn(config=config, run_id=run_id)
    if isinstance(resolved_bundle, CompositeInfrastructureContext) or _has_named_bundle(
        resolved_bundle
    ):
        named_bundle = resolved_bundle
        return BootstrapRuntimeResources(
            run_id=named_bundle.run_id,
            settings=named_bundle.settings,
            logger=named_bundle.logger,
            metrics=named_bundle.metrics,
            tracer=named_bundle.tracer,
            storage=named_bundle.storage,
            lock=named_bundle.lock,
            clock=getattr(named_bundle, "clock", None),
            infra_context=named_bundle,
        )
    raise TypeError(
        "bootstrap_runtime_basics_fn must return CompositeInfrastructureContext "
        "or another named runtime bundle exposing run_id/settings/logger/"
        "metrics/tracer/storage/lock; legacy tuple bundles are no longer supported"
    )


def build_bootstrap_support_services(
    *,
    build_support_services_fn: Callable[..., object],
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    resources: BootstrapRuntimeResources,
) -> object:
    """Resolve support services from the shared resource bundle."""
    if resources.infra_context is None:
        raise TypeError("bootstrap runtime resources must carry infra_context")
    return build_support_services_fn(
        config=config,
        runtime=runtime,
        infra_context=resources.infra_context,
    )


def create_composite_runner_from_plan_impl(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    plan: CompositeBootstrapPlan,
    create_composite_runner_builder_fn: Callable[..., CompositePipelineRunner],
    runner_factory: Callable[..., CompositePipelineRunner],
) -> CompositePipelineRunner:
    """Create the final composite runner from a resolved bootstrap plan."""
    return create_composite_runner_builder_fn(
        config=config,
        runtime=runtime,
        run_id=plan.run_id,
        logger=plan.logger,
        metrics=plan.metrics,
        tracer=plan.tracer,
        lock=plan.lock,
        seed_runner_factory=plan.seed_runner_factory,
        dependencies_runner_factory=plan.dependencies_runner_factory,
        enricher_runner_factory=plan.enricher_runner_factory,
        support_services=plan.support_services,
        runner_factory=runner_factory,
    )


def _has_named_bundle(resolved_bundle: object) -> TypeGuard[_NamedRuntimeBundle]:
    return all(
        hasattr(resolved_bundle, field_name)
        for field_name in (
            "run_id",
            "settings",
            "logger",
            "metrics",
            "tracer",
            "storage",
            "lock",
        )
    )
