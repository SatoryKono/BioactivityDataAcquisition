"""Shared models for workflow-manifest service helpers."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import RunID
from bioetl.domain.workflow import WorkflowConfig

__all__ = ["WorkflowManifestCreateSpec"]


@dataclass(frozen=True, slots=True)
class WorkflowManifestCreateSpec:
    """Normalized inputs required to build an immutable workflow manifest."""

    workflow_run_id: RunID
    config: WorkflowConfig
    launch_context: dict[str, object]
    resumed_from_manifest_id: str | None = None
