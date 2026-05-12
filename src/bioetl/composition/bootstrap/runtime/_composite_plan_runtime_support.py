"""Shared runtime-resource helpers for composite bootstrap planning."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypeGuard, cast

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import (
        ClockPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings


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
        "metrics/tracer/storage/lock"
    )


def build_bootstrap_support_services(
    *,
    build_support_services_fn: Callable[..., object],
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    resources: BootstrapRuntimeResources,
) -> object:
    """Resolve support services from the shared resource bundle."""
    return _call_supported_kwargs(
        build_support_services_fn,
        {
            "config": config,
            "runtime": runtime,
            "infra_context": resources.infra_context or resources,
        },
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


def _call_supported_kwargs(
    build_support_services_fn: Callable[..., object],
    call_kwargs: dict[str, object],
) -> object:
    try:
        parameters = inspect.signature(build_support_services_fn).parameters
    except (TypeError, ValueError):
        return build_support_services_fn(**call_kwargs)

    if any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    ):
        return build_support_services_fn(**call_kwargs)

    supported_kwargs = {
        name: value for name, value in call_kwargs.items() if name in parameters
    }
    return build_support_services_fn(**supported_kwargs)
