# src/bioetl/composition/factories/runner_services.py
"""Runner Services Factory.

Factory for creating application services used by PipelineRunner.
This follows the DI pattern: services are created in composition layer
and injected into PipelineRunner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.lifecycle_orchestrator import LifecycleOrchestrator
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.postrun_service import PostrunService
from bioetl.application.core.preflight_service import PreflightService

# Re-export RunnerServices from application layer for backwards compatibility
from bioetl.application.core.runner_services import RunnerServices
from bioetl.application.observability.observer import PipelineObserver

if TYPE_CHECKING:
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, TracingPort


def build_runner_services(
    config: PipelineConfig,
    runtime: RuntimeConfig,
    services: PipelineServices,
    context: PipelineContext,
    logger: LoggerPort,
    shutdown_signal: ShutdownSignal,
    checkpoint_manager: CheckpointManager,
    lifecycle_service: MedallionLifecycleService,
    tracer: TracingPort | None = None,
) -> RunnerServices:
    """Build RunnerServices bundle.

    Factory function that creates all application services required by PipelineRunner.
    This centralizes service creation in the composition layer.

    Args:
        config: Pipeline configuration.
        runtime: Runtime configuration.
        services: Pipeline services (storage, lock, metrics, etc.).
        context: Pipeline execution context.
        logger: Structured logger.
        shutdown_signal: Shutdown signal for graceful termination.
        checkpoint_manager: Checkpoint manager.
        lifecycle_service: Medallion lifecycle service.
        tracer: Optional tracing port for distributed tracing.

    Returns:
        RunnerServices bundle with all required services.
    """
    lock_manager = LockManager.create(
        lock_port=services.lock,
        run_id=context.run_id,
        provider=config.provider,
        entity_type=config.entity_type,
        run_type=runtime.run_type,
        lock_ttl=runtime.effective_lock_ttl,
        wait_for_lock=runtime.wait_for_lock,
        wait_timeout=runtime.lock_wait_timeout,
        heartbeat_interval=runtime.heartbeat_interval,
        logger=logger,
        shutdown_signal=shutdown_signal,
        checkpoint_manager=checkpoint_manager,
    )

    preflight_service = PreflightService(
        config=config,
        context=context,
        logger=logger,
        metrics=services.metrics,
    )

    postrun_service = PostrunService(
        config=config,
        runtime=runtime,
        services=services,
        logger=logger,
        lifecycle_service=lifecycle_service,
    )

    lifecycle_orchestrator = LifecycleOrchestrator(
        config=config,
        runtime=runtime,
        logger=logger,
        lifecycle_service=lifecycle_service,
    )

    observer = PipelineObserver(
        pipeline_name=config.pipeline_name,
        run_id=context.run_id,
        run_type=runtime.run_type,
        metrics=services.metrics,
        logger=logger,
        tracer=tracer,
    )

    return RunnerServices(
        lock_manager=lock_manager,
        preflight=preflight_service,
        postrun=postrun_service,
        lifecycle_orch=lifecycle_orchestrator,
        observer=observer,
    )


__all__ = ["RunnerServices", "build_runner_services"]
