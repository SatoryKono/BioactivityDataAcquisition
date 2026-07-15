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
    read_optional_text,
    write_latest_scope_catalog,
    write_latest_scope_index,
)
from bioetl.infrastructure.errors import build_storage_error

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
        existing_manifest_id = store._load_manifest_id_for_run_id(manifest.run_id)
        if (
            existing_manifest_id is not None
            and existing_manifest_id != manifest.manifest_id
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
        should_update_scope_index = existing_latest is None or (
            manifest.created_at,
            manifest.manifest_id,
        ) >= (existing_latest.created_at, existing_latest.manifest_id)
        paths_to_write = [manifest_path, run_index_path, catalog_path]
        if should_update_scope_index:
            paths_to_write.append(scope_index_path)
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
]
