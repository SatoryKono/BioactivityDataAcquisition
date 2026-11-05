"""File-backed run-manifest persistence."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, override

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane._file_run_manifest_persistence import (
    persist_manifest,
)
from bioetl.infrastructure.control_plane._file_run_manifest_persistence import (
    restore_predecessor_publication as _restore_predecessor_publication,
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
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text
from bioetl.infrastructure.storage.file_metadata_index import catalog_text_index

__all__ = ["FileRunManifestStore", "RunManifestStoreCorruptionError"]

_MANIFEST_READ_WORKERS = 4


@lru_cache(maxsize=1024)
def _decode_manifest(raw: str) -> RunManifest:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Manifest payload must be a JSON object")
    return RunManifest.from_dict(payload)


def _manifest_is_predecessor_of_indexed(
    base_path: Path,
    manifest_id: str,
    indexed_manifest_id: str,
    *,
    run_id: RunID,
    pipeline_name: str,
    run_type: RunType,
) -> bool:
    """Return whether ``manifest_id`` precedes the indexed manifest.

    A record that is no longer current stays readable by ID when the
    indexed manifest links back through ``predecessor_manifest_id``
    (#12014). Cycles, missing files, and mismatched run identities are not
    predecessors.
    """
    seen: set[str] = set()
    cursor: str | None = indexed_manifest_id
    while cursor is not None and cursor not in seen:
        seen.add(cursor)
        try:
            raw = catalog_text_index.read(base_path / f"{cursor}.json")
        except FileNotFoundError:
            return False
        manifest = _decode_manifest(raw)
        if (
            manifest.run_id != run_id
            or manifest.pipeline_name != pipeline_name
            or manifest.run_type != run_type
        ):
            return False
        cursor = manifest.predecessor_manifest_id
        if cursor == manifest_id:
            return True
    return False


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
    replay_object_verifier: ReplayObjectVerifier | None = None

    def verify_replay_objects(self, manifest: RunManifest) -> dict[str, bool]:
        """Check saved objects against this manifest at read time."""
        if self.replay_object_verifier is None:
            return {}
        return self.replay_object_verifier.verify(manifest)

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

    def restore_predecessor_publication(
        self,
        predecessor: RunManifest,
        successor_manifest_id: str,
    ) -> None:
        """Return current indexes to the predecessor and drop the successor."""
        _restore_predecessor_publication(
            self,
            predecessor=predecessor,
            successor_manifest_id=successor_manifest_id,
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
            manifest_ids = (
                path.stem
                for path in sorted(self.base_path.glob("*.json"))
                if path.is_file()
                if not path.name.endswith(".contract-evidence.json")
            )
            # Windows bind mounts make sequential file/index reads exceed the
            # operator deadline. Bound parallel I/O, retaining the same parser,
            # index validation, exception propagation and deterministic order.
            with ThreadPoolExecutor(max_workers=_MANIFEST_READ_WORKERS) as executor:
                manifests = tuple(
                    sorted(
                        (
                            manifest
                            for manifest in executor.map(
                                self._load_manifest, manifest_ids
                            )
                            if manifest is not None
                        ),
                        key=lambda manifest: (
                            manifest.created_at,
                            manifest.manifest_id,
                        ),
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
        try:
            raw = catalog_text_index.read(manifest_path)
        except FileNotFoundError:
            return None
        manifest = _decode_manifest(raw)
        indexed_manifest_id = self._load_manifest_id_for_run_id(manifest.run_id)
        if indexed_manifest_id != manifest.manifest_id and (
            indexed_manifest_id is None
            or not _manifest_is_predecessor_of_indexed(
                self.base_path,
                manifest.manifest_id,
                indexed_manifest_id,
                run_id=manifest.run_id,
                pipeline_name=manifest.pipeline_name,
                run_type=manifest.run_type,
            )
        ):
            raise RunManifestStoreCorruptionError(
                "Run manifest index corruption: manifest file "
                f"'{manifest.manifest_id}' declares run_id '{manifest.run_id}' "
                f"but the run-id index maps to '{indexed_manifest_id}'"
            )
        return manifest

    def _load_manifest_id_for_run_id(self, run_id: RunID) -> str | None:
        """Return the indexed manifest identifier for one run when present."""
        run_index_path = self.base_path / "_by_run_id" / f"{run_id}.txt"
        try:
            manifest_id = catalog_text_index.read(run_index_path).strip()
        except FileNotFoundError:
            return None
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


_ALREADY_MAPPED = "already mapped to a different manifest_id"


@dataclass(frozen=True, slots=True)
class LiveRootRecordResult:
    """Outcome of one new-run publication into the live catalog."""

    outcome: str
    catalog_snapshot: tuple[str, ...]


def snapshot_manifest_catalog(base_path: Path) -> tuple[str, ...]:
    """Return sorted manifest ids already stored under ``base_path``."""
    if not base_path.is_dir():
        return ()
    return tuple(
        sorted(
            path.stem
            for path in base_path.glob("*.json")
            if path.is_file() and not path.name.endswith(".contract-evidence.json")
        )
    )


def record_manifest_in_live_catalog(
    *,
    manifest: RunManifest,
    live_base: Path,
    source_base: Path,
) -> LiveRootRecordResult:
    """Publish one new manifest into the live catalog.

    Historical data trees are not scanned or copied. Different bytes for an
    existing manifest id stay in place. A run-id index advances only for the
    verified successor of the indexed manifest; the previous file stays.
    Catalog ids present before the write must still be present after it.
    """
    live = Path(live_base)
    source = Path(source_base)
    snapshot = snapshot_manifest_catalog(live)
    if live.resolve(strict=False) == source.resolve(strict=False):
        return LiveRootRecordResult("already_live", snapshot)
    if _kept_existing_manifest(live, manifest):
        _assert_snapshot_preserved(live, snapshot)
        return LiveRootRecordResult("kept_existing", snapshot)
    if _already_recorded(live, manifest):
        _copy_own_contract_evidence(
            manifest.manifest_id, live_base=live, source_base=source
        )
        _assert_snapshot_preserved(live, snapshot)
        return LiveRootRecordResult("already_recorded", snapshot)
    store = FileRunManifestStore(base_path=live)
    try:
        persist_manifest(
            store,
            manifest,
            atomic_writer=atomic_write_text,
            require_local_predecessor=False,
        )
    except ValueError as exc:
        if _ALREADY_MAPPED not in str(exc):
            raise
        _assert_snapshot_preserved(live, snapshot)
        return LiveRootRecordResult("kept_existing", snapshot)
    _copy_own_contract_evidence(
        manifest.manifest_id, live_base=live, source_base=source
    )
    _assert_snapshot_preserved(live, snapshot)
    return LiveRootRecordResult("recorded", snapshot)


def _rendered_manifest(manifest: RunManifest) -> str:
    return json.dumps(manifest.to_dict(), indent=2, sort_keys=True)


def _normalized_manifest_text(text: str) -> str:
    return text.replace("\r\n", "\n").rstrip("\n")


def _kept_existing_manifest(live_base: Path, manifest: RunManifest) -> bool:
    """True when a recorded live file must not be replaced."""
    target = live_base / f"{manifest.manifest_id}.json"
    if target.is_file():
        current = target.read_text(encoding="utf-8")
        if _normalized_manifest_text(current) != _normalized_manifest_text(
            _rendered_manifest(manifest)
        ):
            return True
    index = live_base / "_by_run_id" / f"{manifest.run_id}.txt"
    if not index.is_file():
        return False
    current_id = index.read_text(encoding="utf-8").strip()
    if not current_id or current_id == manifest.manifest_id:
        return False
    return not _verified_successor_of_indexed(live_base, manifest, current_id)


def _verified_successor_of_indexed(
    live_base: Path,
    manifest: RunManifest,
    indexed_id: str,
) -> bool:
    """True when this manifest is the next link of the indexed run."""
    predecessor_id = manifest.predecessor_manifest_id
    if predecessor_id != indexed_id:
        return False
    try:
        predecessor = FileRunManifestStore(base_path=live_base).get(indexed_id)
    except (OSError, TypeError, ValueError):
        return False
    return predecessor is not None and predecessor.run_id == manifest.run_id


def _already_recorded(live_base: Path, manifest: RunManifest) -> bool:
    target = live_base / f"{manifest.manifest_id}.json"
    index = live_base / "_by_run_id" / f"{manifest.run_id}.txt"
    if not target.is_file() or not index.is_file():
        return False
    if index.read_text(encoding="utf-8").strip() != manifest.manifest_id:
        return False
    current = target.read_text(encoding="utf-8")
    return _normalized_manifest_text(current) == _normalized_manifest_text(
        _rendered_manifest(manifest)
    )


def copy_contract_evidence_to_live_catalog(
    manifest_id: str,
    *,
    source_base: Path,
    live_base: Path,
) -> None:
    """Copy one created sidecar onto a manifest already stored in the live catalog.

    The sidecar is published when it is created, not only during the earlier
    manifest write. A missing live manifest is left untouched, and an existing
    sidecar is not replaced.
    """
    live = Path(live_base)
    source = Path(source_base)
    if live.resolve(strict=False) == source.resolve(strict=False):
        return
    if not (live / f"{manifest_id}.json").is_file():
        return
    _copy_own_contract_evidence(manifest_id, live_base=live, source_base=source)


def _copy_own_contract_evidence(
    manifest_id: str,
    *,
    live_base: Path,
    source_base: Path,
) -> None:
    """Copy this publication's sidecar only. Predecessor files stay put."""
    name = f"{manifest_id}.contract-evidence.json"
    source = source_base / name
    destination = live_base / name
    if destination.exists() or not source.is_file():
        return
    atomic_write_text(destination, source.read_text(encoding="utf-8"))


def _assert_snapshot_preserved(base_path: Path, snapshot: tuple[str, ...]) -> None:
    missing = [
        manifest_id
        for manifest_id in snapshot
        if not (base_path / f"{manifest_id}.json").is_file()
    ]
    if missing:
        raise RuntimeError(
            "live manifest catalog lost recorded manifests: " + ", ".join(missing)
        )
