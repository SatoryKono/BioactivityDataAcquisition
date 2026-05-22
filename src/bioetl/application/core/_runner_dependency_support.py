"""Private support helpers for :mod:`bioetl.application.core.runner`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointRuntimeService,
    )
    from bioetl.application.core.lifecycle.lock_runtime_service import (
        LockRuntimeService,
    )
    from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
    from bioetl.application.core.postrun.service import PostrunService
    from bioetl.application.core.preflight.service import PreflightService
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


@dataclass(frozen=True, slots=True)
class PipelineRunnerDependencies:
    """Grouped collaborators for PipelineRunner."""

    executor: BatchExecutor
    checkpoint_manager: CheckpointRuntimeService
    lock_runtime_service: LockRuntimeService
    preflight: PreflightService
    postrun: PostrunService
    lifecycle_service: MedallionLifecycleService
    observer: PipelineObserver
    shutdown_signal: ShutdownSignal

    @property
    def lock_manager(self) -> LockRuntimeService:
        """Legacy alias retained while callers migrate to runtime-service naming."""
        return self.lock_runtime_service


def resolve_runner_dependencies(
    *,
    executor: BatchExecutor | None,
    checkpoint_manager: CheckpointRuntimeService | None,
    shutdown_signal: ShutdownSignal | None,
    lock_runtime_service: LockRuntimeService | None,
    lock_manager: LockRuntimeService | None,
    preflight: PreflightService | None,
    postrun: PostrunService | None,
    lifecycle_service: MedallionLifecycleService | None,
    observer: PipelineObserver | None,
) -> PipelineRunnerDependencies:
    """Resolve transitional constructor parameters into structured dependencies.

    Compatibility shim for legacy direct runner kwargs. Review for removal after
    2026-09-30 once test-only callers migrate to ``PipelineRunnerDependencies``.
    """
    values = {
        "executor": executor,
        "checkpoint_manager": checkpoint_manager,
        "shutdown_signal": shutdown_signal,
        "lock_runtime_service": lock_runtime_service or lock_manager,
        "preflight": preflight,
        "postrun": postrun,
        "lifecycle_service": lifecycle_service,
        "observer": observer,
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        raise AssertionError("PipelineRunner constructor requires all dependencies")
    return PipelineRunnerDependencies(
        executor=cast("BatchExecutor", values["executor"]),
        checkpoint_manager=cast(
            "CheckpointRuntimeService", values["checkpoint_manager"]
        ),
        lock_runtime_service=cast("LockRuntimeService", values["lock_runtime_service"]),
        preflight=cast("PreflightService", values["preflight"]),
        postrun=cast("PostrunService", values["postrun"]),
        lifecycle_service=cast(
            "MedallionLifecycleService",
            values["lifecycle_service"],
        ),
        observer=cast("PipelineObserver", values["observer"]),
        shutdown_signal=cast("ShutdownSignal", values["shutdown_signal"]),
    )


async def load_runner_checkpoint(
    checkpoint_manager: CheckpointRuntimeService,
) -> CheckpointMetadata | dict[str, object] | None:
    """Load checkpoint with the current execution metadata."""
    return await checkpoint_manager.load_checkpoint(
        current_metadata=checkpoint_manager.current_metadata
    )
