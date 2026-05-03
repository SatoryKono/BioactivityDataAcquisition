"""Stable application-core seam for composition-owned pipeline factory wiring."""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.lifecycle import (
    CheckpointRuntimeService,
    LockRuntimeService,
    ShutdownSignal,
)
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.postrun import PostrunService
from bioetl.application.core.preflight import PreflightService
from bioetl.application.core.runner import PipelineRunner, PipelineRunnerDependencies

__all__ = [
    "BasePipeline",
    "BatchExecutor",
    "CheckpointRuntimeService",
    "LockRuntimeService",
    "PipelineRunner",
    "PipelineRunnerDependencies",
    "PipelineService",
    "PostrunService",
    "PreflightService",
    "ShutdownSignal",
]
