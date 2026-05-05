"""File-backed run-manifest persistence."""

from __future__ import annotations

import json
from contextlib import suppress
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
from bioetl.infrastructure.errors import build_storage_error
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileRunManifestStore", "RunManifestStoreCorruptionError"]


class RunManifestStoreCorruptionError(ValueError):
    """Raised when manifest files and run-id indexes disagree."""


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
        "bioetl_control_plane_manifest_writes_total",
        1,
        {
            "pipeline": pipeline,
            "run_type": run_type,
            "status": status,
        },
    )


def _emit_manifest_write_duration_metric(
    metrics: MetricsPort | None,
    *,
    pipeline: str,
    run_type: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Emit one control-plane manifest write duration metric when enabled."""
    if metrics is None:
        return
    metrics.observe_histogram(
        "bioetl_control_plane_manifest_write_duration_seconds",
        duration_seconds,
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
        started_at = perf_counter()
        manifest_path = self.base_path / f"{manifest.manifest_id}.json"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{manifest.run_id}.txt"
        failed_path = manifest_path
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            run_index_dir.mkdir(parents=True, exist_ok=True)
            existing_manifest_id = self._load_manifest_id_for_run_id(manifest.run_id)
            if (
                existing_manifest_id is not None
                and existing_manifest_id != manifest.manifest_id
            ):
                raise ValueError(
                    "run_id is already mapped to a different manifest_id: "
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
            _emit_manifest_write_metric(
                self.metrics,
                pipeline=manifest.pipeline_name,
                run_type=manifest.run_type.value,
                status="failed",
            )
            _emit_manifest_write_duration_metric(
                self.metrics,
                pipeline=manifest.pipeline_name,
                run_type=manifest.run_type.value,
                status="failed",
                duration_seconds=perf_counter() - started_at,
            )
            raise build_storage_error(
                message_prefix="Run manifest",
                operation="save",
                path=failed_path,
                error=error,
                manifest_id=manifest.manifest_id,
                run_id=str(manifest.run_id),
            ) from error
        _emit_manifest_write_metric(
            self.metrics,
            pipeline=manifest.pipeline_name,
            run_type=manifest.run_type.value,
            status="success",
        )
        _emit_manifest_write_duration_metric(
            self.metrics,
            pipeline=manifest.pipeline_name,
            run_type=manifest.run_type.value,
            status="success",
            duration_seconds=perf_counter() - started_at,
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
            manifest_id = self._load_manifest_id_for_run_id(run_id)
            if not manifest_id:
                status = "miss"
                return None
            manifest = self._load_manifest(manifest_id)
            if manifest is None:
                raise RunManifestStoreCorruptionError(
                    "Run manifest index corruption: run-id index points to "
                    f"missing manifest file '{manifest_id}' for run_id '{run_id}'"
                )
            if manifest.run_id != run_id:
                raise RunManifestStoreCorruptionError(
                    "Run manifest index corruption: indexed manifest "
                    f"'{manifest_id}' belongs to run_id '{manifest.run_id}', "
                    f"not requested run_id '{run_id}'"
                )
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
        manifest = RunManifest.from_dict(payload)
        indexed_manifest_id = self._load_manifest_id_for_run_id(manifest.run_id)
        if indexed_manifest_id != manifest.manifest_id:
            raise RunManifestStoreCorruptionError(
                "Run manifest index corruption: manifest file "
                f"'{manifest.manifest_id}' declares run_id '{manifest.run_id}' "
                f"but the run-id index maps to '{indexed_manifest_id}'"
            )
        return manifest

    def _load_manifest_id_for_run_id(self, run_id: RunID) -> str | None:
        """Return the indexed manifest identifier for one run when present."""
        run_index_path = self.base_path / "_by_run_id" / f"{run_id}.txt"
        if not run_index_path.exists():
            return None
        manifest_id = run_index_path.read_text(encoding="utf-8").strip()
        return manifest_id or None

    @staticmethod
    def _rollback_manifest_file(manifest_path: Path) -> None:
        """Remove a manifest file when a later consistency step fails."""
        with suppress(OSError):
            if manifest_path.exists():
                manifest_path.unlink()
