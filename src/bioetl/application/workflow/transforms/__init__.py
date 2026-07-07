"""Transform registry primitives for declarative workflow execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime

from bioetl.application.services.workflow_transform_artifacts import (
    WorkflowTransformArtifactSinkProtocol,
)

type WorkflowTransformOutput = object
type WorkflowTransformCallable = Callable[
    ..., WorkflowTransformOutput | Awaitable[WorkflowTransformOutput]
]


@dataclass(frozen=True, slots=True)
class WorkflowTransformDestructiveCommitSignal:
    """Persistable signal that a destructive transform mutation has committed."""

    step_id: str
    transform_name: str
    fingerprint: str
    details: dict[str, object]


WorkflowTransformDestructiveCommit = WorkflowTransformDestructiveCommitSignal


@dataclass(frozen=True, slots=True)
class WorkflowTransformRuntimeContext:
    """Optional runtime callbacks exposed to transform executors."""

    dry_run: bool = False
    workflow_name: str | None = None
    workflow_run_id: str | None = None
    manifest_id: str | None = None
    debug_export_enabled: bool = False
    debug_export_dir: str | None = None
    artifact_sink: WorkflowTransformArtifactSinkProtocol | None = None
    created_at: datetime | None = None
    destructive_commit_callback: (
        Callable[[WorkflowTransformDestructiveCommit], None] | None
    ) = None

    def record_destructive_commit(
        self,
        *,
        step_id: str,
        transform_name: str,
        fingerprint: str,
        details: dict[str, object],
    ) -> None:
        """Publish one destructive-commit marker when a callback is present."""
        if self.destructive_commit_callback is None:
            return
        self.destructive_commit_callback(
            WorkflowTransformDestructiveCommitSignal(
                step_id=step_id,
                transform_name=transform_name,
                fingerprint=fingerprint,
                details=details,
            )
        )


__all__ = [
    "WorkflowTransformCallable",
    "WorkflowTransformDestructiveCommit",
    "WorkflowTransformDestructiveCommitSignal",
    "WorkflowTransformOutput",
    "WorkflowTransformRegistry",
    "WorkflowTransformRuntimeContext",
]


@dataclass(slots=True)
class WorkflowTransformRegistry:
    """In-memory registry for named workflow transform executors."""

    _executors: dict[str, WorkflowTransformCallable] = field(default_factory=dict)

    def register(
        self,
        transform_name: str,
        executor: WorkflowTransformCallable,
    ) -> None:
        """Register or replace an executor for a declarative transform name."""
        self._executors[transform_name] = executor

    def get(self, transform_name: str) -> WorkflowTransformCallable:
        """Return a registered executor or fail with a bounded error."""
        try:
            return self._executors[transform_name]
        except KeyError as exc:
            raise KeyError(f"Unknown workflow transform: {transform_name}") from exc

    def contains(self, transform_name: str) -> bool:
        """Return whether an executor is registered for the transform name."""
        return transform_name in self._executors
