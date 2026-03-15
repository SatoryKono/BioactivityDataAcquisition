"""Composite runner assembly helpers for runtime bootstrap facade."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import uuid4

from bioetl.application.composite.checkpoint import CompositeCheckpointService
from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.key_extractor import (
    KeyExtractorService as _KeyExtractorService,
)
from bioetl.application.composite.merger import MergeService as _MergeService
from bioetl.application.composite.runner_pkg import CompositePipelineRunnerService
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.fsm_helper import FSMStateHelperService
    from bioetl.application.composite.preflight_validator import (
        CompositePreflightValidator,
    )
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.ports import LockPort, MetricsPort, QuarantinePort
    from bioetl.infrastructure.config import Settings


CompositeRunnerFactory = Callable[..., CompositePipelineRunnerService]


__all__ = [
    "CompositePipelineRunner",
    "bootstrap_composite_pipeline",
    "bootstrap_composite_runner",
    "create_composite_runner",
    "create_composite_runner_with_legacy_fsm_adapter",
]


def create_composite_runner_with_legacy_fsm_adapter(
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
    fsm_state_helper: FSMStateHelperService | None = None,
    run_id: str | None = None,
    dq_report_service: DQReportService | None = None,
    preflight_validator: CompositePreflightValidator | None = None,
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    | None = None,
    dependency_coordinator: DependencyCoordinatorService | None = None,
    quarantine_port: QuarantinePort | None = None,
    metrics: MetricsPort | None = None,
) -> CompositePipelineRunnerService:
    """Create composite runner with temporary legacy FSM injection in composition.

    Returns:
        CompositePipelineRunnerService wired with the provided dependencies.
    """
    effective_run_id = run_id or str(uuid4())
    effective_fsm_state_helper = fsm_state_helper

    if effective_fsm_state_helper is None:
        from bioetl.application.composite.fsm_helper import FSMStateHelperService

        warnings.warn(
            "Creating CompositePipelineRunner without fsm_state_helper is deprecated; "
            "inject fsm_state_helper from composition.",
            DeprecationWarning,
            stacklevel=2,
        )
        effective_fsm_state_helper = FSMStateHelperService(
            config=config,
            logger=logger,
            run_id=effective_run_id,
        )

    return CompositePipelineRunnerService(
        config=config,
        runtime=runtime,
        seed_runner_factory=seed_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        key_extractor=key_extractor,
        coordinator=coordinator,
        merger=merger,
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        lock=lock,
        fsm_state_helper=effective_fsm_state_helper,
        run_id=effective_run_id,
        dq_report_service=dq_report_service,
        preflight_validator=preflight_validator,
        dependencies_runner_factory=dependencies_runner_factory,
        dependency_coordinator=dependency_coordinator,
        quarantine_port=quarantine_port,
        metrics=metrics,
    )


# Backward-compatible patch point used by legacy bootstrap tests.
CompositePipelineRunner = create_composite_runner_with_legacy_fsm_adapter


def create_composite_runner(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str,
    logger: LoggerPort,
    lock: LockPort,
    seed_runner_factory: Callable[[], PipelineRunner],
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    support_services: CompositeSupportServices,
    runner_factory: CompositeRunnerFactory = CompositePipelineRunner,
) -> CompositePipelineRunnerService:
    """Create fully wired CompositePipelineRunner service.

    Returns:
        Fully wired CompositePipelineRunnerService ready for execution.
    """
    return runner_factory(
        config=config,
        runtime=runtime,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        key_extractor=support_services.key_extractor,
        dependency_coordinator=support_services.dependency_coordinator,
        coordinator=support_services.coordinator,
        merger=support_services.merger,
        checkpoint_manager=support_services.checkpoint_manager,
        fsm_state_helper=support_services.fsm_state_helper,
        logger=logger,
        lock=lock,
        run_id=run_id,
        dq_report_service=support_services.dq_report_service,
        quarantine_port=support_services.quarantine_port,
    )


def bootstrap_composite_runner(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
    bootstrap_runtime_basics_fn: Callable[
        ..., tuple[str, Settings, LoggerPort, object, LockPort]
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
    """Assemble and create composite runner with injected dependency builders.

    Args:
        config: Validated CompositeConfig for this composite run.
        runtime: Runtime options (resume, dry_run, cached bronze, etc.).
        run_id: Optional UUID string for this run; generated when None.
        bootstrap_runtime_basics_fn: Callable that provisions base dependencies
            (run_id, settings, logger, storage, lock).
        build_runner_factories_fn: Callable that returns (seed_factory,
            dependency_factory, enricher_factory) tuples.
        build_support_services_fn: Callable that returns CompositeSupportServices.
        create_composite_runner_fn: Callable that assembles the final
            CompositePipelineRunnerService from all dependencies.

    Returns:
        Fully wired CompositePipelineRunnerService ready for execution.
    """
    effective_run_id, settings, logger, storage, lock = bootstrap_runtime_basics_fn(
        config=config,
        run_id=run_id,
    )
    seed_factory, dependency_factory, enricher_factory = build_runner_factories_fn(
        config=config,
        runtime=runtime,
        logger=logger,
    )
    support_services = build_support_services_fn(
        config=config,
        runtime=runtime,
        settings=settings,
        logger=logger,
        storage=storage,
        run_id=effective_run_id,
    )
    return create_composite_runner_fn(
        config=config,
        runtime=runtime,
        run_id=effective_run_id,
        logger=logger,
        lock=lock,
        seed_runner_factory=seed_factory,
        dependencies_runner_factory=dependency_factory,
        enricher_runner_factory=enricher_factory,
        support_services=support_services,
    )


def bootstrap_composite_pipeline(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
    bootstrap_runner_fn: Callable[
        [CompositeConfig, CompositeRuntimeConfig, str | None],
        CompositePipelineRunnerService,
    ],
) -> CompositePipelineRunnerService:
    """Alias wrapper for composite runner bootstrap entry point.

    Args:
        config: Validated CompositeConfig for this composite run.
        runtime: Runtime options for the composite run.
        run_id: Optional UUID string for this run; generated when None.
        bootstrap_runner_fn: Callable implementing the actual bootstrap logic;
            called with (config, runtime, run_id).

    Returns:
        Fully wired CompositePipelineRunnerService ready for execution.
    """
    return bootstrap_runner_fn(config, runtime, run_id)
