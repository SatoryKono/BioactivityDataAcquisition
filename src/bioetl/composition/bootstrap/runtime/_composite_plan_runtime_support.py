# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Shared runtime-resource helpers for composite bootstrap planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from pydantic import ValidationError

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.infrastructure.config.composite_config_api import (
    load_composite_config as _load_composite_config_impl,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from bioetl.application.composite.runner_pkg import CompositePipelineRunner
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.composition.bootstrap.runtime._composite_plan_support import (
        CompositeBootstrapPlan,
    )
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.ports import (
        ClockPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.config.composite_config_api import (
        ConfigPayloadValidator,
    )

@dataclass(frozen=True, slots=True)
class BootstrapRuntimeResources:
    """Resolved runtime-basics bundle shared by bootstrap orchestration."""

    infra_context: CompositeInfrastructureContext

    @property
    def run_id(self) -> str:
        return self.infra_context.run_id

    @property
    def settings(self) -> Settings:
        return self.infra_context.settings

    @property
    def logger(self) -> LoggerPort:
        return self.infra_context.logger

    @property
    def metrics(self) -> MetricsPort:
        return self.infra_context.metrics

    @property
    def tracer(self) -> TracingPort:
        return self.infra_context.tracer

    @property
    def storage(self) -> object:
        return self.infra_context.storage

    @property
    def lock(self) -> LockPort:
        return self.infra_context.lock

    @property
    def clock(self) -> ClockPort | None:
        return self.infra_context.clock

def load_runtime_composite_config_impl(
    name: str,
    *,
    resolve_config_path_fn: Callable[[str], Path],
    validate_payload: ConfigPayloadValidator,
) -> CompositeConfig:
    """Load a composite config through the infrastructure owner API."""
    config_path = resolve_config_path_fn(name)
    try:
        return _load_composite_config_impl(
            config_path.stem,
            config_dir=config_path.parent,
            validate_payload=validate_payload,
        )
    except ValidationError as error:
        raise ValueError(f"Invalid composite config '{name}': {error}") from error

def build_bootstrap_runtime_resources(
    *,
    bootstrap_runtime_basics_fn: Callable[..., object],
    config: CompositeConfig,
    run_id: str | None,
) -> BootstrapRuntimeResources:
    """Resolve the canonical runtime-basics resource bundle."""
    resolved_bundle = bootstrap_runtime_basics_fn(config=config, run_id=run_id)
    if isinstance(resolved_bundle, CompositeInfrastructureContext):
        return BootstrapRuntimeResources(infra_context=resolved_bundle)
    named_context = _coerce_named_runtime_bundle(resolved_bundle)
    if named_context is not None:
        return BootstrapRuntimeResources(infra_context=named_context)
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

def _coerce_named_runtime_bundle(
    resolved_bundle: object,
) -> CompositeInfrastructureContext | None:
    field_names = (
        "run_id",
        "settings",
        "logger",
        "metrics",
        "tracer",
        "storage",
        "lock",
    )
    if not all(hasattr(resolved_bundle, field_name) for field_name in field_names):
        return None
    bundle = cast("CompositeInfrastructureContext", resolved_bundle)
    clock = bundle.clock if hasattr(bundle, "clock") else None
    return CompositeInfrastructureContext(
        run_id=bundle.run_id,
        settings=bundle.settings,
        logger=bundle.logger,
        metrics=bundle.metrics,
        tracer=bundle.tracer,
        storage=bundle.storage,
        lock=bundle.lock,
        clock=clock,
    )
