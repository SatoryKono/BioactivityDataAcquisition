"""Read-only legacy rebuild planning for the latest-manifest scope index."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunType
from bioetl.infrastructure.control_plane._run_manifest_scope_index import (
    LatestScopeIndexCatalog,
    latest_scope_catalog_path,
)


class _ScopeIndexStore(Protocol):
    base_path: Path

    def list_all(self) -> tuple[RunManifest, ...]: ...

    def _latest_scope_index_path(
        self,
        pipeline_name: str,
        run_type: RunType,
    ) -> Path: ...

    def _load_latest_scope_catalog(self) -> LatestScopeIndexCatalog | None: ...

    def _load_latest_scope_manifest(
        self,
        pipeline_name: str,
        run_type: RunType,
    ) -> RunManifest | None: ...


def _relative_posix(path: Path, base_path: Path) -> str:
    """Return platform-independent paths in the serialized rebuild contract."""
    return path.relative_to(base_path).as_posix()


def plan_latest_scope_index_rebuild(store: _ScopeIndexStore) -> dict[str, object]:
    """Build a deterministic report without writing any index file."""
    manifests = store.list_all()
    latest_by_scope: dict[tuple[str, RunType], RunManifest] = {}
    for manifest in manifests:
        latest_by_scope[(manifest.pipeline_name, manifest.run_type)] = manifest
    desired_scopes = tuple(
        sorted(latest_by_scope, key=lambda item: (item[0], item[1].value))
    )
    desired_catalog = LatestScopeIndexCatalog(complete=True, scopes=desired_scopes)

    entries: list[dict[str, object]] = []
    for pipeline_name, run_type in desired_scopes:
        desired = latest_by_scope[(pipeline_name, run_type)]
        corruption: str | None = None
        try:
            current = store._load_latest_scope_manifest(pipeline_name, run_type)
        except ValueError as error:
            current = None
            corruption = str(error)
        action = _rebuild_action(
            corruption=corruption,
            current=current,
            desired=desired,
        )
        entries.append(
            {
                "action": action,
                "corruption": corruption,
                "current_manifest_id": (
                    current.manifest_id if current is not None else None
                ),
                "desired_manifest_id": desired.manifest_id,
                "index_path": _relative_posix(
                    store._latest_scope_index_path(pipeline_name, run_type),
                    store.base_path,
                ),
                "pipeline_name": pipeline_name,
                "run_type": run_type.value,
            }
        )

    catalog_corruption: str | None = None
    try:
        current_catalog = store._load_latest_scope_catalog()
    except ValueError as error:
        current_catalog = None
        catalog_corruption = str(error)
    catalog_action = _catalog_action(
        corruption=catalog_corruption,
        current=current_catalog,
        desired=desired_catalog,
    )
    return {
        "approval_required_before_apply": any(
            entry["action"] != "noop" for entry in entries
        )
        or catalog_action != "noop",
        "catalog": {
            "action": catalog_action,
            "complete": True,
            "corruption": catalog_corruption,
            "index_path": _relative_posix(
                latest_scope_catalog_path(store.base_path), store.base_path
            ),
            "scopes": [
                {"pipeline_name": pipeline_name, "run_type": run_type.value}
                for pipeline_name, run_type in desired_scopes
            ],
        },
        "contract": "run_manifest_latest_scope_index_rebuild_v1",
        "entries": entries,
        "manifest_count": len(manifests),
        "mode": "dry_run",
        "scope_count": len(entries),
        "writes_performed": 0,
    }


def _rebuild_action(
    *,
    corruption: str | None,
    current: RunManifest | None,
    desired: RunManifest,
) -> str:
    if corruption is not None:
        return "blocked_corrupt"
    if current is None:
        return "create"
    return "noop" if current.manifest_id == desired.manifest_id else "update"


def _catalog_action(
    *,
    corruption: str | None,
    current: LatestScopeIndexCatalog | None,
    desired: LatestScopeIndexCatalog,
) -> str:
    if corruption is not None:
        return "blocked_corrupt"
    if current is None:
        return "create"
    return "noop" if current == desired else "update"


__all__ = ["plan_latest_scope_index_rebuild"]
