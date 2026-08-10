"""File-backed run-manifest persistence."""

from __future__ import annotations

import json
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, override

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane._file_run_manifest_persistence import (
    persist_manifest,
)
from bioetl.infrastructure.control_plane._raw_run_manifest_inspection import (
    RawRunManifestInspectionMixin,
)
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)
from bioetl.infrastructure.control_plane._run_manifest_scope_index import (
    LatestScopeIndexCatalog,
    latest_scope_catalog_path,
    latest_scope_index_path,
    load_latest_scope_catalog,
    load_latest_scope_index,
    restore_optional_text,
    write_latest_scope_index,
)
from bioetl.infrastructure.control_plane._run_manifest_scope_rebuild import (
    plan_latest_scope_index_rebuild,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileRunManifestStore", "RunManifestStoreCorruptionError"]


class RunManifestStoreCorruptionError(ValueError):
    """Raised when manifest files and run-id indexes disagree."""


if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


def _load_latest_scope_manifest(
    store: FileRunManifestStore,
    pipeline_name: str,
    run_type: RunType,
) -> RunManifest | None:
    index_path = store._latest_scope_index_path(pipeline_name, run_type)
    try:
        record = load_latest_scope_index(
            index_path,
            pipeline_name=pipeline_name,
            run_type=run_type,
        )
    except (OSError, TypeError, ValueError) as error:
        raise RunManifestStoreCorruptionError(
            f"Run manifest latest-scope index corruption: cannot load '{index_path}'"
        ) from error
    if record is None:
        return None
    manifest = store._load_manifest(record.manifest_id)
    if manifest is None:
        raise RunManifestStoreCorruptionError(
            "Run manifest latest-scope index corruption: index points to "
            f"missing manifest file '{record.manifest_id}'"
        )
    if manifest.pipeline_name != pipeline_name or manifest.run_type != run_type:
        raise RunManifestStoreCorruptionError(
            "Run manifest latest-scope index corruption: indexed manifest "
            f"'{manifest.manifest_id}' belongs to scope "
            f"'{manifest.pipeline_name}/{manifest.run_type.value}', not "
            f"'{pipeline_name}/{run_type.value}'"
        )
    return manifest


@dataclass(slots=True)
class FileRunManifestStore(RawRunManifestInspectionMixin, RunManifestPort):
    """Persist manifests as JSON files under the control-plane output tree."""

    base_path: Path
    metrics: MetricsPort | None = None

    def assert_saved(self, manifest: RunManifest) -> None:
        """Fail closed if a just-saved manifest did not materialize on disk.

        Full reconstruction still lives in ``get``/``get_by_run_id``. This
        post-save hook avoids immediate JSON rehydration on Windows-backed
        temp directories, where read-after-atomic-replace can stall under IDE
        test runners and filesystem sync tools.
        """
        manifest_path = self.base_path / f"{manifest.manifest_id}.json"
        if not manifest_path.is_file():
            raise RuntimeError(
                "Run manifest persistence failed: manifest file is not materialized"
            )
        run_index_path = self.base_path / "_by_run_id" / f"{manifest.run_id}.txt"
        if not run_index_path.is_file():
            raise RuntimeError(
                "Run manifest persistence failed: run_id index is not materialized"
            )
        scope_index_path = self._latest_scope_index_path(
            manifest.pipeline_name,
            manifest.run_type,
        )
        if not scope_index_path.is_file():
            raise RuntimeError(
                "Run manifest persistence failed: latest-scope index is not materialized"
            )
        if not latest_scope_catalog_path(self.base_path).is_file():
            raise RuntimeError(
                "Run manifest persistence failed: latest-scope catalog is not materialized"
            )

    @override
    def save(self, manifest: RunManifest) -> None:
        """Persist manifest JSON and run-id index."""
        persist_manifest(
            self,
            manifest,
            atomic_writer=atomic_write_text,
            scope_index_writer=write_latest_scope_index,
        )

    @override
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

    @override
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

    @override
    def get_latest_for_scope(
        self,
        pipeline_name: str,
        run_types: tuple[RunType, ...] = (),
    ) -> RunManifest | None:
        """Load the latest indexed manifest for one exact pipeline scope."""
        started_at = perf_counter()
        status = "success"
        try:
            bounded_run_types = tuple(
                sorted(set(run_types or tuple(RunType)), key=lambda item: item.value)
            )
            catalog = self._load_latest_scope_catalog()
            if catalog is None or not catalog.complete:
                status = "miss"
                return None
            candidates = tuple(
                manifest
                for run_type in bounded_run_types
                if (pipeline_name, run_type) in catalog.scopes
                for manifest in (
                    self._load_required_latest_scope_manifest(pipeline_name, run_type),
                )
            )
            if not candidates:
                status = "miss"
                return None
            return max(
                candidates,
                key=lambda manifest: (manifest.created_at, manifest.manifest_id),
            )
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="manifest",
                operation="get_latest_for_scope",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    @override
    def list_all(self) -> tuple[RunManifest, ...]:
        """Enumerate every persisted manifest in deterministic order."""
        started_at = perf_counter()
        status = "success"
        try:
            manifests = tuple(
                sorted(
                    (
                        manifest
                        for path in sorted(self.base_path.glob("*.json"))
                        if path.is_file()
                        for manifest in (self._load_manifest(path.stem),)
                        if manifest is not None
                    ),
                    key=lambda manifest: (manifest.created_at, manifest.manifest_id),
                )
            )
            if not manifests:
                status = "miss"
            return manifests
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="manifest",
                operation="list_all",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def plan_latest_scope_index_rebuild(self) -> dict[str, object]:
        """Build a deterministic, read-only rebuild plan for legacy data."""
        return plan_latest_scope_index_rebuild(self)

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

    def _latest_scope_index_path(
        self,
        pipeline_name: str,
        run_type: RunType,
    ) -> Path:
        return latest_scope_index_path(self.base_path, pipeline_name, run_type)

    def _load_latest_scope_catalog(self) -> LatestScopeIndexCatalog | None:
        catalog_path = latest_scope_catalog_path(self.base_path)
        try:
            return load_latest_scope_catalog(catalog_path)
        except (OSError, TypeError, ValueError) as error:
            raise RunManifestStoreCorruptionError(
                "Run manifest latest-scope index corruption: "
                f"cannot load catalog '{catalog_path}'"
            ) from error

    def _load_latest_scope_manifest(
        self,
        pipeline_name: str,
        run_type: RunType,
    ) -> RunManifest | None:
        return _load_latest_scope_manifest(self, pipeline_name, run_type)

    def _load_required_latest_scope_manifest(
        self,
        pipeline_name: str,
        run_type: RunType,
    ) -> RunManifest:
        manifest = self._load_latest_scope_manifest(pipeline_name, run_type)
        if manifest is None:
            raise RunManifestStoreCorruptionError(
                "Run manifest latest-scope index corruption: catalog scope "
                f"'{pipeline_name}/{run_type.value}' has no pointer record"
            )
        return manifest

    @staticmethod
    def _restore_save_transaction(rollback_state: dict[Path, str | None]) -> None:
        """Best-effort restore of files changed by a failed save transaction."""
        for path, previous in reversed(tuple(rollback_state.items())):
            with suppress(OSError):
                restore_optional_text(path, previous)
