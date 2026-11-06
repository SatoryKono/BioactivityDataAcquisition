"""Publish run manifests and finalized evidence to the live catalog."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.control_plane import RunManifest
from bioetl.infrastructure.control_plane._file_run_manifest_persistence import (
    persist_manifest,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = [
    "LiveRootRecordResult",
    "copy_contract_evidence_to_live_catalog",
    "record_manifest_in_live_catalog",
    "snapshot_manifest_catalog",
]

_ALREADY_MAPPED = "run_id is already mapped to a different manifest_id"


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
