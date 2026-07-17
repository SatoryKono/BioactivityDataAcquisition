"""Stable application-core seam for composition-owned pipeline factory wiring.

This compatibility facade preserves historical imports without eagerly loading
the full application-core graph during module initialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.wiring._lazy_export_facade import (
    install_lazy_export_facade,
)

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline as BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor as BatchExecutor
    from bioetl.application.core.lifecycle import (
        CheckpointRuntimeService as CheckpointRuntimeService,
    )
    from bioetl.application.core.lifecycle import (
        LockRuntimeService as LockRuntimeService,
    )
    from bioetl.application.core.lifecycle import (
        ShutdownSignal as ShutdownSignal,
    )
    from bioetl.application.core.pipeline_services import (
        PipelineService as PipelineService,
    )
    from bioetl.application.core.postrun import PostrunService as PostrunService
    from bioetl.application.core.preflight import PreflightService as PreflightService
    from bioetl.application.core.runner import (
        PipelineRunner as PipelineRunner,
    )
    from bioetl.application.core.runner import (
        PipelineRunnerDependencies as PipelineRunnerDependencies,
    )

_PUBLIC_EXPORTS = {
    "BasePipeline": ("bioetl.application.core.base", "BasePipeline"),
    "BatchExecutor": ("bioetl.application.core.batch_executor", "BatchExecutor"),
    "CheckpointRuntimeService": (
        "bioetl.application.core.lifecycle",
        "CheckpointRuntimeService",
    ),
    "LockRuntimeService": (
        "bioetl.application.core.lifecycle",
        "LockRuntimeService",
    ),
    "PipelineRunner": ("bioetl.application.core.runner", "PipelineRunner"),
    "PipelineRunnerDependencies": (
        "bioetl.application.core.runner",
        "PipelineRunnerDependencies",
    ),
    "PipelineService": (
        "bioetl.application.core.pipeline_services",
        "PipelineService",
    ),
    "PostrunService": ("bioetl.application.core.postrun", "PostrunService"),
    "PreflightService": ("bioetl.application.core.preflight", "PreflightService"),
    "ShutdownSignal": ("bioetl.application.core.lifecycle", "ShutdownSignal"),
}

install_lazy_export_facade(globals(), __name__, _PUBLIC_EXPORTS)

__all__: list[str]
