"""Runner services bundle.

Dataclass bundling services injected into PipelineRunner via DI.
This bundle is created in the composition layer and passed to the runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle_orchestrator import LifecycleOrchestrator
    from bioetl.application.core.lock_manager import LockManager
    from bioetl.application.core.postrun_service import PostrunService
    from bioetl.application.core.preflight_service import PreflightService
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.domain.locking import LockContextHolder


@dataclass(frozen=True)
class RunnerServices:
    """Bundle of services injected into PipelineRunner.

    Attributes:
        lock_manager: Distributed locking manager.
        preflight: Pre-flight infrastructure validation service.
        postrun: Post-run DQ checks and VACUUM service.
        lifecycle_orch: Lifecycle orchestrator for medallion layer clearing.
        observer: Pipeline observability wrapper for tracing, metrics, and logging.
        context_holder: Shared holder for lock context (optional).
    """

    lock_manager: LockManager
    preflight: PreflightService
    postrun: PostrunService
    lifecycle_orch: LifecycleOrchestrator
    observer: PipelineObserver
    context_holder: LockContextHolder | None = None
