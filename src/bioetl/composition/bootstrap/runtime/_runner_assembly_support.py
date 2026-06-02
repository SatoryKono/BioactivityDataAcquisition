"""Composite runner assembly helpers for runtime bootstrap."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
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
from bioetl.composition.occurrence_identity import create_runtime_occurrence_id
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import (
        CompositePreflightValidationService,
        FSMStateHelperService,
        PipelineRunner,
    )
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import (
        ClockPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )


@dataclass(frozen=True, slots=True)
class CompositeRunnerServiceInputs:
    config: CompositeConfig
    runtime: CompositeRuntimeConfig
    run_id: str | None
    logger: LoggerPort
    lock: LockPort
    seed_runner_factory: Callable[[], PipelineRunner]
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    key_extractor: _KeyExtractorService
    coordinator: EnrichmentCoordinatorService
    merger: _MergeService
    checkpoint_manager: CompositeCheckpointService
    fsm_state_helper: FSMStateHelperService | None
    dq_report_service: DQReportService | None
    preflight_validator: CompositePreflightValidationService | None
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner] | None
    dependency_coordinator: DependencyCoordinatorService | None
    quarantine_port: QuarantinePort | None
    metrics: MetricsPort | None
    tracer: TracingPort | None
    observer: CompositeLifecycleObserverService | None
    manifest_id: str | None
    run_ledger_service: RunLedgerService | None
    clock: ClockPort | None = None


CompositeRunnerFactory = Callable[..., CompositePipelineRunner]


def resolve_effective_run_id(run_id: str | None) -> str:
    return run_id or create_runtime_occurrence_id("composite_runner")


def _requires_explicit_control_plane_run_id(
    inputs: CompositeRunnerServiceInputs,
) -> bool:
    return inputs.manifest_id is not None or inputs.run_ledger_service is not None


def build_composite_runner_dependencies(
    inputs: CompositeRunnerServiceInputs,
) -> CompositeRunnerDependencies:
    effective_clock = inputs.clock or SystemClock()
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
        clock=effective_clock,
    )


def build_composite_runner_service_inputs(
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
) -> CompositeRunnerServiceInputs:
    return CompositeRunnerServiceInputs(
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
        clock=SystemClock(),
    )


def normalize_composite_runner_service_inputs(
    inputs: CompositeRunnerServiceInputs,
) -> CompositeRunnerServiceInputs:
    if inputs.fsm_state_helper is None:
        raise AssertionError("Composite runner requires fsm_state_helper")
    if inputs.observer is None:
        inputs = replace(
            inputs,
            observer=CompositeLifecycleObserverService(
                logger=inputs.logger,
                metrics=inputs.metrics,
                tracer=inputs.tracer,
            ),
        )
    if inputs.run_id is None:
        if _requires_explicit_control_plane_run_id(inputs):
            raise ValueError(
                "Composite runner control-plane assembly requires explicit run_id"
            )
        inputs = replace(inputs, run_id=resolve_effective_run_id(inputs.run_id))
    return inputs


def invoke_composite_runner_factory(
    *,
    runner_factory: CompositeRunnerFactory,
    inputs: CompositeRunnerServiceInputs,
) -> CompositePipelineRunner:
    return runner_factory(inputs)


def create_composite_runner_service_from_inputs(
    inputs: CompositeRunnerServiceInputs,
) -> CompositePipelineRunner:
    normalized_inputs = normalize_composite_runner_service_inputs(inputs)
    effective_run_id = normalized_inputs.run_id or resolve_effective_run_id(
        normalized_inputs.run_id
    )
    deps = build_composite_runner_dependencies(normalized_inputs)
    return CompositePipelineRunner(
        config=normalized_inputs.config,
        runtime=normalized_inputs.runtime,
        deps=deps,
        run_id=effective_run_id,
    )
