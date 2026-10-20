# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Transactional persistence helpers for file-backed run manifests."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunManifest
from bioetl.infrastructure.control_plane._run_manifest_scope_index import (
    LatestScopeIndexCatalog,
    LatestScopeIndexRecord,
    latest_scope_catalog_path,
    load_latest_scope_index,
    read_optional_text,
    write_latest_scope_catalog,
    write_latest_scope_index,
)
from bioetl.infrastructure.errors import build_storage_error
from bioetl.infrastructure.storage.atomic import atomic_write_text

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.infrastructure.control_plane.file_run_manifest_store import (
        FileRunManifestStore,
    )


@dataclass(slots=True)
class _WriteProgress:
    """Track the file whose write is currently in progress."""

    failed_path: Path


def emit_manifest_write_metric(
    metrics: MetricsPort | None,
    *,
    pipeline: str,
    run_type: str,
    status: str,
) -> None:
    """Emit one control-plane manifest write metric when enabled."""
    if metrics is None:
        return
    metrics.increment_counter(
        "bioetl_control_plane_manifest_writes_total",
        0,
        {
            "pipeline": pipeline,
            "run_type": run_type,
            "status": "failed" if status == "success" else "success",
        },
    )
    metrics.increment_counter(
        "bioetl_control_plane_manifest_writes_total",
        1,
        {"pipeline": pipeline, "run_type": run_type, "status": status},
    )


def emit_manifest_write_duration_metric(
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
        {"pipeline": pipeline, "run_type": run_type, "status": status},
    )


def _emit_write_metrics(
    metrics: MetricsPort | None,
    manifest: RunManifest,
    *,
    status: str,
    started_at: float,
) -> None:
    """Emit the counter and duration for one manifest write outcome."""
    emit_manifest_write_metric(
        metrics,
        pipeline=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        status=status,
    )
    emit_manifest_write_duration_metric(
        metrics,
        pipeline=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        status=status,
        duration_seconds=perf_counter() - started_at,
    )


def _should_update_scope_index(
    manifest: RunManifest,
    existing_latest: RunManifest | None,
) -> bool:
    """Return whether this save should move the latest-scope pointer.

    A successor of the current latest record is newer even when its
    manifest id sorts lower. ``created_at`` is copied from the
    predecessor, and runtime ids are not time-ordered.
    """
    if existing_latest is None:
        return True
    if manifest.predecessor_manifest_id == existing_latest.manifest_id:
        return True
    return (manifest.created_at, manifest.manifest_id) >= (
        existing_latest.created_at,
        existing_latest.manifest_id,
    )


def _rebind_contract_evidence_identity(text: str, manifest_id: str) -> str:
    """Point a copied sidecar at the successor when it names a manifest."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    if not isinstance(payload, dict) or "manifest_id" not in payload:
        return text
    if payload.get("manifest_id") == manifest_id:
        return text
    payload["manifest_id"] = manifest_id
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if text.endswith("\n"):
        rendered += "\n"
    return rendered


def _inherited_contract_evidence(
    base_path: Path,
    manifest: RunManifest,
) -> tuple[Path, str] | None:
    """Copy a predecessor sidecar onto a successor that does not have one."""
    predecessor_id = manifest.predecessor_manifest_id
    if not predecessor_id:
        return None
    source = base_path / f"{predecessor_id}.contract-evidence.json"
    destination = base_path / f"{manifest.manifest_id}.contract-evidence.json"
    if destination.exists() or not source.is_file():
        return None
    inherited = source.read_text(encoding="utf-8")
    return destination, _rebind_contract_evidence_identity(
        inherited,
        manifest.manifest_id,
    )


def _write_manifest_files(
    manifest: RunManifest,
    *,
    manifest_path: Path,
    run_index_path: Path,
    scope_index_path: Path,
    catalog_path: Path,
    updated_catalog: LatestScopeIndexCatalog,
    should_update_scope_index: bool,
    atomic_writer: Callable[..., None],
    scope_index_writer: Callable[..., None],
    progress: _WriteProgress,
) -> None:
    """Write manifest and indexes after the transaction state is captured."""
    progress.failed_path = manifest_path
    atomic_writer(
        manifest_path,
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
    )
    progress.failed_path = run_index_path
    atomic_writer(run_index_path, manifest.manifest_id)
    if should_update_scope_index:
        progress.failed_path = scope_index_path
        scope_index_writer(
            scope_index_path,
            LatestScopeIndexRecord(
                pipeline_name=manifest.pipeline_name,
                run_type=manifest.run_type,
                manifest_id=manifest.manifest_id,
            ),
        )
    progress.failed_path = catalog_path
    write_latest_scope_catalog(catalog_path, updated_catalog)


def restore_predecessor_publication(
    store: FileRunManifestStore,
    *,
    predecessor: RunManifest,
    successor_manifest_id: str,
) -> None:
    """Drop a successor publication after the ledger rebind did not commit.

    The known-scope catalog stays. It records which scopes exist, not which
    manifest is current.
    """
    successor_id = successor_manifest_id.strip()
    run_index_path = store.base_path / "_by_run_id" / f"{predecessor.run_id}.txt"
    if run_index_path.is_file():
        current_id = run_index_path.read_text(encoding="utf-8").strip()
        if current_id == successor_id:
            atomic_write_text(run_index_path, predecessor.manifest_id)
    scope_path = store._latest_scope_index_path(
        predecessor.pipeline_name,
        predecessor.run_type,
    )
    scope_record = load_latest_scope_index(
        scope_path,
        pipeline_name=predecessor.pipeline_name,
        run_type=predecessor.run_type,
    )
    if scope_record is not None and scope_record.manifest_id == successor_id:
        write_latest_scope_index(
            scope_path,
            LatestScopeIndexRecord(
                pipeline_name=predecessor.pipeline_name,
                run_type=predecessor.run_type,
                manifest_id=predecessor.manifest_id,
            ),
        )
    successor_manifest = store.base_path / f"{successor_id}.json"
    successor_evidence = store.base_path / f"{successor_id}.contract-evidence.json"
    successor_manifest.unlink(missing_ok=True)
    successor_evidence.unlink(missing_ok=True)


def persist_manifest(
    store: FileRunManifestStore,
    manifest: RunManifest,
    *,
    atomic_writer: Callable[..., None],
    scope_index_writer: Callable[..., None] = write_latest_scope_index,
) -> None:
    """Persist one manifest and all indexes as one rollback-aware transaction."""
    started_at = perf_counter()
    manifest_path = store.base_path / f"{manifest.manifest_id}.json"
    run_index_path = store.base_path / "_by_run_id" / f"{manifest.run_id}.txt"
    scope_index_path = store._latest_scope_index_path(
        manifest.pipeline_name, manifest.run_type
    )
    catalog_path = latest_scope_catalog_path(store.base_path)
    progress = _WriteProgress(failed_path=manifest_path)
    rollback_state: dict[Path, str | None] = {}
    try:
        store.base_path.mkdir(parents=True, exist_ok=True)
        run_index_path.parent.mkdir(parents=True, exist_ok=True)
        predecessor_id = getattr(manifest, "predecessor_manifest_id", None)
        if isinstance(predecessor_id, str) and predecessor_id.strip():
            predecessor = store.get(predecessor_id)
            if predecessor is None:
                raise ValueError(f"predecessor manifest {predecessor_id!r} is missing")
            if predecessor.run_id != manifest.run_id:
                raise ValueError(
                    "predecessor_manifest_id belongs to a different run_id: "
                    f"{predecessor.run_id}"
                )
        existing_manifest_id = store._load_manifest_id_for_run_id(manifest.run_id)
        if (
            existing_manifest_id is not None
            and existing_manifest_id != manifest.manifest_id
            and getattr(manifest, "predecessor_manifest_id", None)
            != existing_manifest_id
        ):
            raise ValueError(
                "run_id is already mapped to a different manifest_id: "
                f"{existing_manifest_id}"
            )
        catalog = store._load_latest_scope_catalog()
        if catalog is None:
            catalog = LatestScopeIndexCatalog(
                complete=not any(store.base_path.glob("*.json")), scopes=()
            )
        updated_catalog = LatestScopeIndexCatalog(
            complete=catalog.complete,
            scopes=tuple(
                sorted(
                    {*catalog.scopes, (manifest.pipeline_name, manifest.run_type)},
                    key=lambda item: (item[0], item[1].value),
                )
            ),
        )
        existing_latest = store._load_latest_scope_manifest(
            manifest.pipeline_name, manifest.run_type
        )
        should_update_scope_index = _should_update_scope_index(
            manifest, existing_latest
        )
        paths_to_write = [manifest_path, run_index_path, catalog_path]
        if should_update_scope_index:
            paths_to_write.append(scope_index_path)
        inherited_evidence = _inherited_contract_evidence(store.base_path, manifest)
        if inherited_evidence is not None:
            paths_to_write.append(inherited_evidence[0])
        rollback_state = {path: read_optional_text(path) for path in paths_to_write}
        _write_manifest_files(
            manifest,
            manifest_path=manifest_path,
            run_index_path=run_index_path,
            scope_index_path=scope_index_path,
            catalog_path=catalog_path,
            updated_catalog=updated_catalog,
            should_update_scope_index=should_update_scope_index,
            atomic_writer=atomic_writer,
            scope_index_writer=scope_index_writer,
            progress=progress,
        )
        if inherited_evidence is not None:
            evidence_path, evidence_text = inherited_evidence
            progress.failed_path = evidence_path
            atomic_writer(evidence_path, evidence_text)
    except (OSError, TypeError, ValueError) as error:
        store._restore_save_transaction(rollback_state)
        _emit_write_metrics(
            store.metrics,
            manifest,
            status="failed",
            started_at=started_at,
        )
        raise build_storage_error(
            message_prefix="Run manifest",
            operation="save",
            path=progress.failed_path,
            error=error,
            manifest_id=manifest.manifest_id,
            run_id=str(manifest.run_id),
        ) from error
    _emit_write_metrics(
        store.metrics,
        manifest,
        status="success",
        started_at=started_at,
    )


__all__ = [
    "emit_manifest_write_duration_metric",
    "emit_manifest_write_metric",
    "persist_manifest",
    "restore_predecessor_publication",
]
