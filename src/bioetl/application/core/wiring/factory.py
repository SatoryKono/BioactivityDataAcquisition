"""Stable application-core seam for composition-owned pipeline factory wiring.

This compatibility facade preserves historical imports without eagerly loading
the full application-core graph during module initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

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

__all__ = list(_PUBLIC_EXPORTS)


def __getattr__(name: str) -> object:
    export = _PUBLIC_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = export
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
