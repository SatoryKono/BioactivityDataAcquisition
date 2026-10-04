"""Composite runner assembly facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    CompositeRunnerFactory,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    build_composite_runner_service_inputs as _build_composite_runner_service_inputs_impl,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    create_composite_runner_service_from_inputs as create_composite_runner_service,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    invoke_composite_runner_factory as _invoke_composite_runner_factory_impl,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.ports import LoggerPort
from bioetl.composition.bootstrap.runtime.runner_bootstrap_wiring import (
    bootstrap_composite_runner_via_wiring as bootstrap_composite_runner,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_wiring_api import (
        PipelineRunner,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.ports import (
        LockPort,
        MetricsPort,
        TracingPort,
    )

__all__ = [
    "bootstrap_composite_runner",
    "create_composite_runner",
    "create_composite_runner_service",
]


def create_composite_runner(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    tracer: TracingPort | None,
    lock: LockPort,
    seed_runner_factory: Callable[[], PipelineRunner],
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    support_services: CompositeSupportServices,
    runner_factory: CompositeRunnerFactory = create_composite_runner_service,
) -> CompositePipelineRunner:
    """Create a fully wired ``CompositePipelineRunner``."""
    service_inputs = _build_composite_runner_service_inputs_impl(
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
    return _invoke_composite_runner_factory_impl(
        runner_factory=runner_factory,
        inputs=service_inputs,
    )
