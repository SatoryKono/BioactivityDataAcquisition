"""Private support helpers for :mod:`bioetl.application.core.runner`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

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


async def load_runner_checkpoint(
    checkpoint_manager: CheckpointRuntimeService,
) -> CheckpointMetadata | dict[str, object] | None:
    """Load checkpoint with the current execution metadata."""
    return await checkpoint_manager.load_checkpoint(
        current_metadata=checkpoint_manager.current_metadata
    )
