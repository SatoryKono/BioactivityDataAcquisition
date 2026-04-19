"""Composite runner assembly facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.composite.runtime_wiring_api import (
    CompositeCheckpointService,
    CompositeLifecycleObserverService,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    CompositeRunnerFactory,
    CompositeRunnerServiceInputs,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    build_composite_runner_service_inputs as _build_composite_runner_service_inputs_impl,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    create_composite_runner_service_from_inputs as _create_composite_runner_service_from_inputs_impl,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    invoke_composite_runner_factory as _invoke_composite_runner_factory_impl,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    resolve_effective_run_id as _resolve_effective_run_id_impl,
)
from bioetl.composition.bootstrap.runtime.runner_bootstrap_wiring import (
    bootstrap_composite_runner_via_wiring,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_wiring_api import (
        CompositePreflightValidationService,
        DependencyCoordinatorService,
        EnrichmentCoordinatorService,
        FSMStateHelperService,
        PipelineRunner,
    )
    from bioetl.application.composite.runtime_wiring_api import (
        KeyExtractorService as _KeyExtractorService,
    )
    from bioetl.application.composite.runtime_wiring_api import (
        MergeService as _MergeService,
    )
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.ports import LockPort, MetricsPort, QuarantinePort, TracingPort
    from bioetl.infrastructure.config import Settings


__all__ = [
    "bootstrap_composite_runner",
    "create_composite_runner",
    "create_composite_runner_service",
]


def create_composite_runner_service(
    inputs: CompositeRunnerServiceInputs,
) -> CompositePipelineRunner:
    """Create a composite runner service from fully resolved dependencies."""
    return _create_composite_runner_service_from_inputs_impl(inputs)


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


def bootstrap_composite_runner(
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
    """Assemble and create a composite runner via injected dependency builders."""
    return bootstrap_composite_runner_via_wiring(
        config=config,
        runtime=runtime,
        run_id=run_id,
        bootstrap_runtime_basics_fn=bootstrap_runtime_basics_fn,
        build_runner_factories_fn=build_runner_factories_fn,
        build_support_services_fn=build_support_services_fn,
        create_composite_runner_fn=create_composite_runner_fn,
    )
