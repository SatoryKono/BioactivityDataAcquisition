"""Shared immutable input-snapshot resolution helpers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.service import (
    collect_manifest_input_snapshot_refs as collect_manifest_input_snapshot_refs,
)
from bioetl.application.services.control_plane.manifest.service import (
    resolve_input_snapshot_refs,
)

from bioetl.composition.runtime_builders.cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
    require_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.control_plane_paths import (
    control_plane_root,
)
from bioetl.domain.control_plane import RunInputSnapshotRef
from bioetl.infrastructure.control_plane import FileRunManifestStore

if TYPE_CHECKING:
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "collect_manifest_input_snapshot_refs",
    "resolve_cached_bronze_input_snapshot_refs",
    "resolve_manifest_input_snapshot_refs",
    "resolve_pipeline_input_snapshot_refs",
]


def resolve_cached_bronze_input_snapshot_refs(
    *,
    cached_bronze: CachedBronzeContext | None,
    settings: Settings,
    provider: str,
    entity: str,
    require: bool = False,
) -> tuple[RunInputSnapshotRef, ...]:
    """Resolve immutable snapshots from one cached-Bronze runtime context."""
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()
    bronze_path = getattr(cached_bronze, "bronze_path", None)
    bronze_date = getattr(cached_bronze, "bronze_date", None)
    bronze_root = (
        Path(str(bronze_path))
        if bronze_path is not None
        else Path(str(settings.bronze_path)) / provider / entity
    )
    loader = (
        require_cached_bronze_input_snapshot_refs
        if require
        else build_cached_bronze_input_snapshot_refs
    )
    return loader(
        bronze_root=bronze_root,
        bronze_date=_coerce_optional_str(bronze_date),
    )


def resolve_manifest_input_snapshot_refs(
    *,
    settings: Settings,
    manifest_id: str | None = None,
    run_id: str | None = None,
) -> tuple[RunInputSnapshotRef, ...]:
    """Resolve immutable snapshots from one persisted manifest."""
    return resolve_input_snapshot_refs(
        manifest_port=FileRunManifestStore(
            base_path=control_plane_root(settings, "run_manifest"),
        ),
        manifest_id=manifest_id,
        run_id=run_id,
    )


def resolve_pipeline_input_snapshot_refs(
    *,
    ctx: PipelineRunContext,
    cached_bronze: CachedBronzeContext | None,
    settings: Settings,
    provider: str,
    entity: str,
    require_cached_bronze: bool = False,
) -> tuple[RunInputSnapshotRef, ...]:
    """Resolve immutable snapshot evidence for one executable pipeline launch."""
    cached_bronze_enabled = cached_bronze is not None and bool(
        getattr(cached_bronze, "enabled", False)
    )
    cached_bronze_refs = resolve_cached_bronze_input_snapshot_refs(
        cached_bronze=cached_bronze,
        settings=settings,
        provider=provider,
        entity=entity,
        require=require_cached_bronze,
    )
    # Cached-only resolution does not need a store or writable data-root setup.
    manifest_port = None
    if not cached_bronze_enabled and not cached_bronze_refs:
        manifest_port = FileRunManifestStore(
            base_path=control_plane_root(settings, "run_manifest"),
        )
    return resolve_input_snapshot_refs(
        manifest_port=manifest_port,
        cached_bronze_enabled=cached_bronze_enabled,
        cached_bronze_refs=cached_bronze_refs,
        manifest_id=_coerce_optional_str(getattr(ctx, "replay_of_manifest_id", None)),
        run_id=_coerce_optional_str(getattr(ctx, "replay_of_run_id", None)),
    )


def _coerce_optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
