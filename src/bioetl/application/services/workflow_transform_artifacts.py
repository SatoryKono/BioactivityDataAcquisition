"""Application contracts for workflow transform result artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

__all__ = [
    "WorkflowTransformArtifactContext",
    "WorkflowTransformArtifactSink",
    "artifact_refs_as_dicts",
]


@dataclass(frozen=True, slots=True)
class WorkflowTransformArtifactContext:
    """Runtime metadata required to persist one workflow transform artifact."""

    workflow_name: str
    workflow_run_id: str | None = None
    manifest_id: str | None = None
    step_id: str | None = None
    transform_name: str | None = None
    debug_export_enabled: bool = False
    debug_export_dir: str | None = None
    created_at: datetime | None = None


class WorkflowTransformArtifactSink(Protocol):
    """Persist workflow transform result and optional debug artifacts."""

    def write_reconcile_result_artifact(
        self,
        *,
        context: WorkflowTransformArtifactContext,
        payload: Mapping[str, object],
    ) -> tuple[Mapping[str, object], ...]:
        """Persist the compact normal-mode reconcile result artifact."""
        ...

    def write_reconcile_debug_artifacts(
        self,
        *,
        context: WorkflowTransformArtifactContext,
        request: object,
        result: object,
        retained_rows: tuple[Mapping[str, object], ...],
        orphan_rows: tuple[Mapping[str, object], ...],
    ) -> tuple[Mapping[str, object], ...]:
        """Persist row-level debug artifacts for one reconcile result."""
        ...


def artifact_refs_as_dicts(
    refs: tuple[Mapping[str, object], ...],
) -> tuple[dict[str, object], ...]:
    """Return artifact refs as JSON-friendly dictionaries."""
    return tuple(dict(ref) for ref in refs)
