"""Internal builder helpers for composite runtime bootstrap.

This module holds orchestration internals so ``composite.py`` can remain
as a thin compatibility facade with stable patch points.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_bootstrap_runtime_resources,
)
from bioetl.composition.bootstrap.runtime.runner_assembly import (
    create_composite_runner as _create_composite_runner_impl,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    bootstrap_runtime_basics as _bootstrap_runtime_basics_impl,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    build_runner_factories,
    build_support_services,
)
from bioetl.infrastructure.time import SystemClock

__all__ = [
    "bootstrap_runtime_basics",
    "build_runner_factories",
    "build_support_services",
    "create_composite_runner",
]


def bootstrap_runtime_basics(
    *,
    config: CompositeConfig,
    run_id: str | None,
    settings_provider: Callable[[], Settings],
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort],
    tracer_bootstrapper: Callable[[Settings], TracingPort],
    storage_bootstrapper: Callable[..., object],
    lock_factory: Callable[[], LockPort],
    uuid_factory: Callable[[], UUID],
) -> CompositeInfrastructureContext:
    """Build base runtime dependencies shared across composite bootstrap.

    Args:
        config: Validated CompositeConfig used to derive the pipeline name.
        run_id: Optional run UUID string; a new UUID is generated when None.
        settings_provider: Callable returning global Settings.
        logger_bootstrapper: Callable accepting (pipeline_name, run_uuid, log_level)
            and returning a LoggerPort.
        storage_bootstrapper: Callable returning a storage adapter (any type).
        lock_factory: Callable returning a LockPort implementation.
        uuid_factory: Callable returning a new UUID (injectable for testing).

    Returns:
        Infrastructure context handoff for the composite run.
    """
    runtime_resources = build_bootstrap_runtime_resources(
        bootstrap_runtime_basics_fn=_bootstrap_runtime_basics_impl,
        config=config,
        run_id=run_id,
    )
    return CompositeInfrastructureContext(
        run_id=runtime_resources.run_id,
        settings=runtime_resources.settings,
        logger=runtime_resources.logger,
        metrics=runtime_resources.metrics,
        tracer=runtime_resources.tracer,
        storage=runtime_resources.storage,
        lock=runtime_resources.lock,
        clock=SystemClock(),
    )


if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import (
        CompositePipelineRunner,
        PipelineRunner,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings


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
    runner_factory: Callable[..., CompositePipelineRunner],
) -> CompositePipelineRunner:
    """Create fully wired CompositePipelineRunner.

    Args:
        config: CompositeConfig for this composite run.
        runtime: Runtime options for the composite run.
        run_id: UUID string identifying this run.
        logger: Structured logger forwarded to the runner.
        lock: LockPort used for runtime execution safety.
        seed_runner_factory: Callable that creates a seed-phase PipelineRunner.
        dependencies_runner_factory: Callable that creates a dependency-phase
            PipelineRunner given a pipeline name and keys DataFrame.
        enricher_runner_factory: Callable that creates an enricher-phase
            PipelineRunner given a pipeline name and keys DataFrame.
        support_services: Bundle of support services (checkpoint, merger, etc.).
        runner_factory: Factory callable used to instantiate
            CompositePipelineRunner with all wired dependencies.

    Returns:
        Fully wired CompositePipelineRunner ready for execution.
    """
    return _create_composite_runner_impl(
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
        runner_factory=runner_factory,
    )
