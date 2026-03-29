"""File-backed run-manifest persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)

__all__ = ["FileRunManifestStore"]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


def _emit_manifest_write_metric(
    metrics: MetricsPort | None,
    *,
    pipeline: str,
    run_type: str,
    status: str,
) -> None:
    """Emit one control-plane manifest write metric when metrics are enabled."""
    if metrics is None:
        return
    metrics.increment_counter(
        "control_plane_manifest_writes_total",
        1,
        {
            "pipeline": pipeline,
            "run_type": run_type,
            "status": status,
        },
    )


@dataclass(slots=True)
class FileRunManifestStore(RunManifestPort):
    """Persist manifests as JSON files under the control-plane output tree."""

    base_path: Path
    metrics: MetricsPort | None = None

    def save(self, manifest: RunManifest) -> None:
        """Persist manifest JSON and run-id index."""
        manifest_path = self.base_path / f"{manifest.manifest_id}.json"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{manifest.run_id}.txt"
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            run_index_dir.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            run_index_path.write_text(manifest.manifest_id, encoding="utf-8")
        except (OSError, TypeError, ValueError):
            _emit_manifest_write_metric(
                self.metrics,
                pipeline=manifest.pipeline_name,
                run_type=manifest.run_type.value,
                status="failed",
            )
            raise
        _emit_manifest_write_metric(
            self.metrics,
            pipeline=manifest.pipeline_name,
            run_type=manifest.run_type.value,
            status="success",
        )

    def get(self, manifest_id: str) -> RunManifest | None:
        """Load a manifest by identifier if present."""
        started_at = perf_counter()
        status = "success"
        try:
            manifest = self._load_manifest(manifest_id)
            if manifest is None:
                status = "miss"
                return None
            return manifest
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="manifest",
                operation="get",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
        """Resolve run-id index to manifest identifier."""
        started_at = perf_counter()
        status = "success"
        try:
            run_index_path = self.base_path / "_by_run_id" / f"{run_id}.txt"
            if not run_index_path.exists():
                status = "miss"
                return None
            manifest_id = run_index_path.read_text(encoding="utf-8").strip()
            if not manifest_id:
                status = "miss"
                return None
            manifest = self._load_manifest(manifest_id)
            if manifest is None:
                status = "miss"
                return None
            return manifest
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="manifest",
                operation="get_by_run_id",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def _load_manifest(self, manifest_id: str) -> RunManifest | None:
        """Load one manifest payload without emitting public lookup metrics."""
        manifest_path = self.base_path / f"{manifest_id}.json"
        if not manifest_path.exists():
            return None
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Manifest payload must be a JSON object")
        return RunManifest.from_dict(payload)
