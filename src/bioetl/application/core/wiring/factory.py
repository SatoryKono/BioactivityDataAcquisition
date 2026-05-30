"""Stable application-core seam for composition-owned pipeline factory wiring.

This compatibility facade preserves historical imports without eagerly loading
the full application-core graph during module initialization.
"""

from __future__ import annotations

from bioetl.application.core.wiring._lazy_export_facade import (
    install_lazy_export_facade,
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
