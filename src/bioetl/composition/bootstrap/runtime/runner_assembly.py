"""Composite runner assembly facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
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
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_wiring_api import (
        CompositeCheckpointService,
        CompositeLifecycleObserverService,
        CompositePreflightValidationService,
        DependencyCoordinatorService,
        EnrichmentCoordinatorService,
        FSMStateHelperService,
        KeyExtractorService,
        MergeService,
        PipelineRunner,
    )
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.ports import (
        ClockPort,
        LockPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )
    from bioetl.infrastructure.config._base import Settings


__all__ = [
    "bootstrap_composite_runner",
    "create_composite_runner",
    "create_composite_runner_service",
]


def create_composite_runner_service(
    inputs: CompositeRunnerServiceInputs | None = None,
    **kwargs: object,
) -> CompositePipelineRunner:
    """Create a composite runner service from fully resolved dependencies.

    Accept both the structured ``inputs`` object and keyword-expanded wiring so
    bootstrap seams can stay assertion-friendly in tests.
    """
    if inputs is None:
        inputs = CompositeRunnerServiceInputs(
            config=cast(CompositeConfig, kwargs["config"]),
            runtime=cast(CompositeRuntimeConfig, kwargs["runtime"]),
            run_id=cast(str | None, kwargs.get("run_id")),
            logger=cast(LoggerPort, kwargs["logger"]),
            lock=cast(LockPort, kwargs["lock"]),
            seed_runner_factory=cast(
                "Callable[[], PipelineRunner]",
                kwargs["seed_runner_factory"],
            ),
            enricher_runner_factory=cast(
                "Callable[[str, pl.DataFrame], PipelineRunner]",
                kwargs["enricher_runner_factory"],
            ),
            key_extractor=cast("KeyExtractorService", kwargs["key_extractor"]),
            coordinator=cast("EnrichmentCoordinatorService", kwargs["coordinator"]),
            merger=cast("MergeService", kwargs["merger"]),
            checkpoint_manager=cast(
                "CompositeCheckpointService",
                kwargs["checkpoint_manager"],
            ),
            fsm_state_helper=cast(
                "FSMStateHelperService | None",
                kwargs.get("fsm_state_helper"),
            ),
            dq_report_service=cast(
                "DQReportService | None",
                kwargs.get("dq_report_service"),
            ),
            preflight_validator=cast(
                "CompositePreflightValidationService | None",
                kwargs.get("preflight_validator"),
            ),
            dependencies_runner_factory=cast(
                "Callable[[str, pl.DataFrame], PipelineRunner] | None",
                kwargs.get("dependencies_runner_factory"),
            ),
            dependency_coordinator=cast(
                "DependencyCoordinatorService | None",
                kwargs.get("dependency_coordinator"),
            ),
            quarantine_port=cast(
                "QuarantinePort | None", kwargs.get("quarantine_port")
            ),
            metrics=cast("MetricsPort | None", kwargs.get("metrics")),
            tracer=cast("TracingPort | None", kwargs.get("tracer")),
            observer=cast(
                "CompositeLifecycleObserverService | None",
                kwargs.get("observer"),
            ),
            manifest_id=cast(str | None, kwargs.get("manifest_id")),
            run_ledger_service=cast(
                "RunLedgerService | None",
                kwargs.get("run_ledger_service"),
            ),
            clock=cast("ClockPort | None", kwargs.get("clock")),
        )
    elif kwargs:
        unexpected = ", ".join(sorted(kwargs))
        raise TypeError(
            "create_composite_runner_service received both inputs and keyword "
            f"arguments: {unexpected}"
        )
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
    from bioetl.composition.bootstrap.runtime.runner_bootstrap_wiring import (
        bootstrap_composite_runner_via_wiring,
    )

    return bootstrap_composite_runner_via_wiring(
        config=config,
        runtime=runtime,
        run_id=run_id,
        bootstrap_runtime_basics_fn=bootstrap_runtime_basics_fn,
        build_runner_factories_fn=build_runner_factories_fn,
        build_support_services_fn=build_support_services_fn,
        create_composite_runner_fn=create_composite_runner_fn,
    )
