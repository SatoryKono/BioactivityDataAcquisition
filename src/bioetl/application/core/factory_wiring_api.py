"""Legacy flat facade for composition-owned pipeline factory wiring."""

from __future__ import annotations
# ruff: noqa: I001

from bioetl.application.core.wiring.factory import (
    BasePipeline as BasePipeline,
    BatchExecutor as BatchExecutor,
    CheckpointRuntimeService as CheckpointRuntimeService,
    LockRuntimeService as LockRuntimeService,
    PipelineRunner as PipelineRunner,
    PipelineRunnerDependencies as PipelineRunnerDependencies,
    PipelineService as PipelineService,
    PostrunService as PostrunService,
    PreflightService as PreflightService,
    ShutdownSignal as ShutdownSignal,
)

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
