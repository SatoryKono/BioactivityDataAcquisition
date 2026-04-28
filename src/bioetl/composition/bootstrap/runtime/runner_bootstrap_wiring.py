"""Internal wiring helpers for composite runner bootstrap assembly."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_bootstrap_runner_factories,
    build_bootstrap_runtime_resources,
    build_bootstrap_support_services,
)
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
    runtime_resources = build_bootstrap_runtime_resources(
        bootstrap_runtime_basics_fn=bootstrap_runtime_basics_fn,
        config=config,
        run_id=run_id,
    )
    seed_runner_factory, dependencies_runner_factory, enricher_runner_factory = (
        build_bootstrap_runner_factories(
            build_runner_factories_fn=build_runner_factories_fn,
            config=config,
            runtime=runtime,
            logger=runtime_resources.logger,
        )
    )
    support_services = build_bootstrap_support_services(
        build_support_services_fn=build_support_services_fn,
        config=config,
        runtime=runtime,
        resources=runtime_resources,
        include_legacy_runtime_kwargs=True,
    )
    return create_composite_runner_fn(
        config=config,
        runtime=runtime,
        run_id=runtime_resources.run_id,
        logger=runtime_resources.logger,
        metrics=runtime_resources.metrics,
        tracer=runtime_resources.tracer,
        lock=runtime_resources.lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        support_services=support_services,
    )
