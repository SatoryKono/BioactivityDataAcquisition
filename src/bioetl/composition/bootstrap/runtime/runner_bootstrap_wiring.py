"""Internal wiring helpers for composite runner bootstrap assembly."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_composite_bootstrap_plan_impl,
    create_composite_runner_from_plan_impl,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    create_composite_runner_service_from_inputs,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.ports import LockPort
    from bioetl.infrastructure.config.settings_api import Settings


def bootstrap_composite_runner_via_wiring(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
    bootstrap_runtime_basics_fn: Callable[
        ...,
        tuple[str, Settings, LoggerPort, MetricsPort, TracingPort, object, LockPort]
        | CompositeInfrastructureContext,
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
    plan = build_composite_bootstrap_plan_impl(
        bootstrap_runtime_basics_fn=bootstrap_runtime_basics_fn,
        config=config,
        runtime=runtime,
        run_id=run_id,
        build_runner_factories_fn=build_runner_factories_fn,
        build_support_services_fn=build_support_services_fn,
    )
    return create_composite_runner_from_plan_impl(
        config=config,
        runtime=runtime,
        plan=plan,
        create_composite_runner_builder_fn=create_composite_runner_fn,
        runner_factory=create_composite_runner_service_from_inputs,
    )
