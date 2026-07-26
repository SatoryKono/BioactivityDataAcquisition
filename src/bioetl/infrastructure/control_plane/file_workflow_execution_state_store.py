"""File-backed workflow execution-state persistence."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from uuid import UUID

from bioetl.domain.control_plane import WorkflowExecutionState
from bioetl.domain.ports import MetricsPort, WorkflowExecutionStatePort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)
from bioetl.infrastructure.errors import build_storage_error
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileWorkflowExecutionStateStore"]


@dataclass(slots=True)
class FileWorkflowExecutionStateStore(WorkflowExecutionStatePort):
    """Persist workflow execution-state owner artifacts as JSON files."""

    base_path: Path
    metrics: MetricsPort | None = None

    def save(self, state: WorkflowExecutionState) -> None:
        """Persist workflow execution state and its indexes."""
        state_path = self.base_path / f"{state.workflow_run_id}.json"
        run_index_dir = self.base_path / "_by_manifest_id"
        run_index_path = run_index_dir / f"{state.manifest_id}.txt"
        latest_dir = self.base_path / "_latest_by_workflow"
        latest_path = latest_dir / f"{state.workflow_name}.txt"
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            run_index_dir.mkdir(parents=True, exist_ok=True)
            latest_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_text(
                state_path,
                json.dumps(state.to_dict(), indent=2, sort_keys=True),
            )
            atomic_write_text(run_index_path, str(state.workflow_run_id))
            atomic_write_text(latest_path, str(state.workflow_run_id))
        except (OSError, TypeError, ValueError) as error:
            raise build_storage_error(
                message_prefix="Workflow execution state",
                operation="save",
                path=state_path,
                error=error,
                manifest_id=state.manifest_id,
                run_id=str(state.workflow_run_id),
            ) from error

    def get_by_run_id(self, workflow_run_id: RunID) -> WorkflowExecutionState | None:
        """Load workflow execution state by run identifier."""
        return self._load_with_metrics(
            operation="get_by_run_id",
            loader=lambda: self._load_state(workflow_run_id),
        )

    def get_by_manifest_id(self, manifest_id: str) -> WorkflowExecutionState | None:
        """Load workflow execution state by manifest identifier."""
        return self._load_with_metrics(
            operation="get_by_manifest_id",
            loader=lambda: self._load_by_manifest_id(manifest_id),
        )

    def get_latest(self, workflow_name: str) -> WorkflowExecutionState | None:
        """Load the latest workflow execution state for a workflow name."""
        return self._load_with_metrics(
            operation="get_latest",
            loader=lambda: self._load_latest(workflow_name),
        )

    def _load_with_metrics(
        self,
        *,
        operation: str,
        loader: Callable[[], WorkflowExecutionState | None],
    ) -> WorkflowExecutionState | None:
        started_at = perf_counter()
        status = "success"
        try:
            state = loader()
            if state is None:
                status = "miss"
            return state
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="workflow_state",
                operation=operation,
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def _load_state(self, workflow_run_id: RunID) -> WorkflowExecutionState | None:
        state_path = self.base_path / f"{workflow_run_id}.json"
        if not state_path.exists():
            return None
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Workflow execution-state payload must be a JSON object")
        return WorkflowExecutionState.from_dict(payload)

    def _load_by_manifest_id(self, manifest_id: str) -> WorkflowExecutionState | None:
        run_index_path = self.base_path / "_by_manifest_id" / f"{manifest_id}.txt"
        if not run_index_path.exists():
            return None
        run_id = run_index_path.read_text(encoding="utf-8").strip()
        if not run_id:
            return None
        return self._load_state(RunID(UUID(run_id)))

    def _load_latest(self, workflow_name: str) -> WorkflowExecutionState | None:
        latest_path = self.base_path / "_latest_by_workflow" / f"{workflow_name}.txt"
        if not latest_path.exists():
            return None
        run_id = latest_path.read_text(encoding="utf-8").strip()
        if not run_id:
            return None
        return self._load_state(RunID(UUID(run_id)))
