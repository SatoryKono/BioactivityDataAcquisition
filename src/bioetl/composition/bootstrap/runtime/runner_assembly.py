"""Composite runner assembly helpers for runtime bootstrap facade."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.composite.runtime_wiring_api import (
    CompositeCheckpointService,
    CompositeLifecycleObserverService,
    CompositeRunnerDependencies,
    DependencyCoordinatorService,
    EnrichmentCoordinatorService,
)
from bioetl.application.composite.runtime_wiring_api import (
    KeyExtractorService as _KeyExtractorService,
)
from bioetl.application.composite.runtime_wiring_api import (
    MergeService as _MergeService,
)
from bioetl.composition.bootstrap.runtime.runner_bootstrap_wiring import (
    bootstrap_composite_runner_via_wiring,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_wiring_api import (
        CompositePreflightValidator,
        FSMStateHelperService,
        PipelineRunner,
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


CompositeRunnerFactory = Callable[..., CompositePipelineRunner]


__all__ = [
    "bootstrap_composite_runner",
    "create_composite_runner",
    "create_composite_runner_service",
]


@dataclass(frozen=True, slots=True)
class _CompositeRunnerServiceInputs:
    """Typed payload passed between composite runner assembly seams."""

    config: CompositeConfig
    runtime: CompositeRuntimeConfig
    run_id: str
    logger: LoggerPort
    lock: LockPort
    seed_runner_factory: Callable[[], PipelineRunner]
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    key_extractor: _KeyExtractorService
    coordinator: EnrichmentCoordinatorService
    merger: _MergeService
    checkpoint_manager: CompositeCheckpointService
    fsm_state_helper: FSMStateHelperService
    dq_report_service: DQReportService | None
    preflight_validator: CompositePreflightValidator | None
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner] | None
    dependency_coordinator: DependencyCoordinatorService | None
    quarantine_port: QuarantinePort | None
    metrics: MetricsPort | None
    tracer: TracingPort | None
    observer: CompositeLifecycleObserverService
    manifest_id: str | None
    run_ledger_service: RunLedgerService | None


def _resolve_effective_run_id(run_id: str | None) -> str:
    """Return caller-provided run_id or generate a UUID."""
    return run_id or str(uuid4())


def _build_composite_runner_dependencies(
    inputs: _CompositeRunnerServiceInputs,
) -> CompositeRunnerDependencies:
    """Bundle runner dependencies before service construction."""
    return CompositeRunnerDependencies(
        seed_runner_factory=inputs.seed_runner_factory,
        enricher_runner_factory=inputs.enricher_runner_factory,
        key_extractor=inputs.key_extractor,
        coordinator=inputs.coordinator,
        merger=inputs.merger,
        checkpoint_manager=inputs.checkpoint_manager,
        logger=inputs.logger,
        lock=inputs.lock,
        fsm_state_helper=inputs.fsm_state_helper,
        dq_report_service=inputs.dq_report_service,
        preflight_validator=inputs.preflight_validator,
        dependencies_runner_factory=inputs.dependencies_runner_factory,
        dependency_coordinator=inputs.dependency_coordinator,
        quarantine_port=inputs.quarantine_port,
        metrics=inputs.metrics,
        tracer=inputs.tracer,
        observer=inputs.observer,
        manifest_id=inputs.manifest_id,
        run_ledger_service=inputs.run_ledger_service,
    )


def _build_composite_runner_service_inputs(
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
) -> _CompositeRunnerServiceInputs:
    """Expand support-service bundle into typed runner-service construction inputs."""
    return _CompositeRunnerServiceInputs(
        config=config,
        runtime=runtime,
        run_id=run_id,
        logger=logger,
        lock=lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        coordinator=support_services.coordinator,
        checkpoint_manager=support_services.checkpoint_manager,
        key_extractor=support_services.key_extractor,
        merger=support_services.merger,
        fsm_state_helper=support_services.fsm_state_helper,
        dq_report_service=support_services.dq_report_service,
        preflight_validator=None,
        dependency_coordinator=support_services.dependency_coordinator,
        quarantine_port=support_services.quarantine_port,
        metrics=metrics,
        tracer=tracer,
        observer=CompositeLifecycleObserverService(
            logger=logger,
            metrics=metrics,
            tracer=tracer,
        ),
        manifest_id=getattr(support_services, "manifest_id", None),
        run_ledger_service=getattr(support_services, "run_ledger_service", None),
    )


def _invoke_composite_runner_factory(
    *,
    runner_factory: CompositeRunnerFactory,
    inputs: _CompositeRunnerServiceInputs,
) -> CompositePipelineRunner:
    """Invoke the final runner factory from a typed assembly payload."""
    return runner_factory(
        config=inputs.config,
        runtime=inputs.runtime,
        seed_runner_factory=inputs.seed_runner_factory,
        enricher_runner_factory=inputs.enricher_runner_factory,
        key_extractor=inputs.key_extractor,
        coordinator=inputs.coordinator,
        merger=inputs.merger,
        checkpoint_manager=inputs.checkpoint_manager,
        logger=inputs.logger,
        lock=inputs.lock,
        fsm_state_helper=inputs.fsm_state_helper,
        run_id=inputs.run_id,
        dq_report_service=inputs.dq_report_service,
        preflight_validator=inputs.preflight_validator,
        dependencies_runner_factory=inputs.dependencies_runner_factory,
        dependency_coordinator=inputs.dependency_coordinator,
        quarantine_port=inputs.quarantine_port,
        metrics=inputs.metrics,
        tracer=inputs.tracer,
        observer=inputs.observer,
        manifest_id=inputs.manifest_id,
        run_ledger_service=inputs.run_ledger_service,
    )


def _create_composite_runner_service_from_inputs(
    inputs: _CompositeRunnerServiceInputs,
) -> CompositePipelineRunner:
    """Construct CompositePipelineRunnerService from a pre-expanded payload."""
    deps = _build_composite_runner_dependencies(inputs)
    return CompositePipelineRunner(
        config=inputs.config,
        runtime=inputs.runtime,
        deps=deps,
        run_id=inputs.run_id,
    )


def create_composite_runner_service(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    seed_runner_factory: Callable[[], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    key_extractor: _KeyExtractorService,
    coordinator: EnrichmentCoordinatorService,
    merger: _MergeService,
    checkpoint_manager: CompositeCheckpointService,
    logger: LoggerPort,
    lock: LockPort,
    fsm_state_helper: FSMStateHelperService,
    run_id: str | None = None,
    dq_report_service: DQReportService | None = None,
    preflight_validator: CompositePreflightValidator | None = None,
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    | None = None,
    dependency_coordinator: DependencyCoordinatorService | None = None,
    quarantine_port: QuarantinePort | None = None,
    metrics: MetricsPort | None = None,
    tracer: TracingPort | None = None,
    observer: CompositeLifecycleObserverService | None = None,
    manifest_id: str | None = None,
    run_ledger_service: RunLedgerService | None = None,
) -> CompositePipelineRunnerService:
    """Create a composite runner service from fully resolved dependencies."""
    if fsm_state_helper is None:
        raise AssertionError("Composite runner requires fsm_state_helper")
    inputs = _CompositeRunnerServiceInputs(
        config=config,
        runtime=runtime,
        run_id=_resolve_effective_run_id(run_id),
        logger=logger,
        lock=lock,
        seed_runner_factory=seed_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        key_extractor=key_extractor,
        coordinator=coordinator,
        merger=merger,
        checkpoint_manager=checkpoint_manager,
        fsm_state_helper=fsm_state_helper,
        dq_report_service=dq_report_service,
        preflight_validator=preflight_validator,
        dependencies_runner_factory=dependencies_runner_factory,
        dependency_coordinator=dependency_coordinator,
        quarantine_port=quarantine_port,
        metrics=metrics,
        tracer=tracer,
        observer=observer
        or CompositeLifecycleObserverService(
            logger=logger,
            metrics=metrics,
            tracer=tracer,
        ),
        manifest_id=manifest_id,
        run_ledger_service=run_ledger_service,
    )
    return _create_composite_runner_service_from_inputs(inputs)


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
) -> CompositePipelineRunnerService:
    """Create a fully wired ``CompositePipelineRunnerService``."""
    service_inputs = _build_composite_runner_service_inputs(
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
    return _invoke_composite_runner_factory(
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
    create_composite_runner_fn: Callable[..., CompositePipelineRunnerService],
) -> CompositePipelineRunnerService:
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
