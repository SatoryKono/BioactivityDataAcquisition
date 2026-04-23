"""Support helpers for constructing run manifest payloads."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition.runtime_builders._cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._run_manifest_contract_identity import (
    resolve_contract_identity,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    ManifestControlPlaneRefs,
    build_planned_artifacts,
    control_plane_root,
    create_control_plane_refs,
    resolve_run_context_values,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    build_launch_context_snapshot,
    normalize_snapshot,
    resolve_provider_entity,
    resolve_replay_parentage,
    to_serializable_mapping,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunSourceRef,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings

__all__ = [
    "ManifestControlPlaneRefs",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "normalize_snapshot",
    "resolve_contract_identity",
    "resolve_provider_entity",
    "resolve_replay_capability",
    "resolve_replay_parentage",
    "resolve_run_context_values",
    "to_serializable_mapping",
]


def build_run_source_refs(
    *,
    ctx: PipelineRunContext,
    cached_bronze: object | None,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunSourceRef, ...]:
    input_snapshots = _build_cached_bronze_snapshot_refs(
        cached_bronze=cached_bronze,
        settings=settings,
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
    )
    if getattr(ctx, "exact_replay", False) and not input_snapshots:
        raise RuntimeError(
            "Exact replay requires immutable input snapshots; no snapshot-backed source refs were resolved for this run"
        )
    return (
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=ctx.pipeline_name,
            query=getattr(ctx, "query", None),
            input_snapshots=input_snapshots,
        ),
    )


def resolve_replay_capability(
    *,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
) -> ReplayCapability:
    has_input_snapshots = any(ref.input_snapshots for ref in source_refs)
    if has_input_snapshots:
        return ReplayCapability.EXACT_REPLAY_SUPPORTED
    if resume_requested:
        return ReplayCapability.RESUME_ONLY
    return ReplayCapability.REBUILD_ONLY


def _build_cached_bronze_snapshot_refs(
    *,
    cached_bronze: object | None,
    settings: Settings,
    pipeline_name: str,
    provider: str,
    entity: str,
) -> tuple[RunInputSnapshotRef, ...]:
    """Build immutable snapshot refs for cached-Bronze executions."""
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()
    bronze_path = getattr(cached_bronze, "bronze_path", None)
    bronze_date = getattr(cached_bronze, "bronze_date", None)
    bronze_root = (
        Path(str(bronze_path))
        if bronze_path is not None
        else settings.bronze_path / provider / entity
    )
    snapshot_refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date=cast("str | None", bronze_date),
    )
    if not snapshot_refs:
        raise RuntimeError(
            "Cached Bronze execution requires at least one persisted batch file for snapshot provenance"
        )
    return snapshot_refs
