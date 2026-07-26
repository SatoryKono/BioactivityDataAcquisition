"""File-backed workflow-manifest persistence."""

from __future__ import annotations

import json
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from bioetl.domain.control_plane import WorkflowManifest
from bioetl.domain.ports import MetricsPort, WorkflowManifestPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)
from bioetl.infrastructure.errors import build_storage_error
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileWorkflowManifestStore"]


@dataclass(slots=True)
class FileWorkflowManifestStore(WorkflowManifestPort):
    """Persist workflow manifests as JSON files under the control-plane tree."""

    base_path: Path
    metrics: MetricsPort | None = None

    def save(self, manifest: WorkflowManifest) -> None:
        """Persist one workflow manifest and its run-id index."""
        manifest_path = self.base_path / f"{manifest.manifest_id}.json"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{manifest.workflow_run_id}.txt"
        failed_path = manifest_path
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            run_index_dir.mkdir(parents=True, exist_ok=True)
            existing_manifest_id = self._load_manifest_id_for_run_id(
                manifest.workflow_run_id
            )
            if (
                existing_manifest_id is not None
                and existing_manifest_id != manifest.manifest_id
            ):
                raise ValueError(
                    "workflow_run_id is already mapped to a different manifest_id: "
                    f"{existing_manifest_id}"
                )
            atomic_write_text(
                manifest_path,
                json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
            )
            failed_path = run_index_path
            atomic_write_text(run_index_path, manifest.manifest_id)
        except (OSError, TypeError, ValueError) as error:
            if failed_path == run_index_path:
                self._rollback_manifest_file(manifest_path)
            raise build_storage_error(
                message_prefix="Workflow manifest",
                operation="save",
                path=failed_path,
                error=error,
                manifest_id=manifest.manifest_id,
                run_id=str(manifest.workflow_run_id),
            ) from error

    def get(self, manifest_id: str) -> WorkflowManifest | None:
        """Load a workflow manifest by identifier."""
        started_at = perf_counter()
        status = "success"
        try:
            manifest = self._load_manifest(manifest_id)
            if manifest is None:
                status = "miss"
            return manifest
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="workflow_manifest",
                operation="get",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def get_by_run_id(self, workflow_run_id: RunID) -> WorkflowManifest | None:
        """Resolve one workflow manifest through the run-id index."""
        started_at = perf_counter()
        status = "success"
        try:
            manifest_id = self._load_manifest_id_for_run_id(workflow_run_id)
            if not manifest_id:
                status = "miss"
                return None
            manifest = self._load_manifest(manifest_id)
            if manifest is None:
                raise ValueError(
                    "Workflow manifest index corruption: run-id index points to "
                    f"missing manifest file '{manifest_id}'"
                )
            return manifest
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="workflow_manifest",
                operation="get_by_run_id",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def list_all(self) -> tuple[WorkflowManifest, ...]:
        """List all workflow manifests in deterministic creation order."""
        started_at = perf_counter()
        status = "success"
        try:
            manifests = [
                manifest
                for path in self.base_path.glob("*.json")
                if (manifest := self._load_manifest(path.stem)) is not None
            ]
            return tuple(
                sorted(
                    manifests,
                    key=lambda manifest: (manifest.created_at, manifest.manifest_id),
                )
            )
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="workflow_manifest",
                operation="list_all",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def _load_manifest(self, manifest_id: str) -> WorkflowManifest | None:
        manifest_path = self.base_path / f"{manifest_id}.json"
        if not manifest_path.exists():
            return None
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Workflow manifest payload must be a JSON object")
        return WorkflowManifest.from_dict(payload)

    def _load_manifest_id_for_run_id(self, workflow_run_id: RunID) -> str | None:
        run_index_path = self.base_path / "_by_run_id" / f"{workflow_run_id}.txt"
        if not run_index_path.exists():
            return None
        manifest_id = run_index_path.read_text(encoding="utf-8").strip()
        return manifest_id or None

    @staticmethod
    def _rollback_manifest_file(manifest_path: Path) -> None:
        with suppress(OSError):
            if manifest_path.exists():
                manifest_path.unlink()
