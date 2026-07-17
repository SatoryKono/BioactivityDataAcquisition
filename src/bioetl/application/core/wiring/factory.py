"""Stable application-core seam for composition-owned pipeline factory wiring.

This compatibility facade preserves historical imports without eagerly loading
the full application-core graph during module initialization. Static exports
are declared in the adjacent stub.
"""

from __future__ import annotations

from bioetl.application.core.wiring._lazy_export_facade import (
    install_lazy_export_facade,
)

_PUBLIC_EXPORTS = {
    "BasePipeline": "bioetl.application.core.base",
    "BatchExecutor": "bioetl.application.core.batch_executor",
    "CheckpointRuntimeService": "bioetl.application.core.lifecycle",
    "LockRuntimeService": "bioetl.application.core.lifecycle",
    "PipelineRunner": "bioetl.application.core.runner",
    "PipelineRunnerDependencies": "bioetl.application.core.runner",
    "PipelineService": "bioetl.application.core.pipeline_services",
    "PostrunService": "bioetl.application.core.postrun",
    "PreflightService": "bioetl.application.core.preflight",
    "ShutdownSignal": "bioetl.application.core.lifecycle",
}

install_lazy_export_facade(globals(), __name__, _PUBLIC_EXPORTS)

__all__: list[str]
