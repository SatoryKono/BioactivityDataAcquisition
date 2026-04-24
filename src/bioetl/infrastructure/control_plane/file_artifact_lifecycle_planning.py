"""Planning helpers for file-backed control-plane artifact lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePolicy,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads import (
    _artifact_id,
    _effective_config_artifact_id,
    _input_snapshot_ids,
    _is_payload_stale,
    _lineage_fragment_id_candidates,
    _manifest_or_run_is_protected,
    _optional_text,
    _payload_text,
    _read_json_object_or_empty,
    _resolve_lifecycle_reason,
    _resolve_payload_or_file_time,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_reasons import (
    _protected_by,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_types import (
    _ProtectedRefs,
)

__all__ = ["_ProtectedRefs", "_iter_artifact_refs", "_resolve_protected_refs"]

_INDEX_DIR_NAMES = {
    "_by_fragment_id",
    "_by_manifest_id",
    "_by_node_id",
    "_by_run_id",
    "_occurrences",
}


@dataclass(slots=True)
class _ProtectedRefAccumulator:
    """Mutable protected-reference accumulator used during planning."""

    manifest_ids: set[str]
    run_ids: set[str]
    input_snapshot_ids: set[str]
    effective_config_artifact_ids: set[str]
    lineage_fragment_ids: set[str]

    @classmethod
    def from_policy(
        cls,
        policy: ControlPlaneArtifactLifecyclePolicy,
    ) -> _ProtectedRefAccumulator:
        return cls(
            manifest_ids=set(policy.protected_manifest_ids),
            run_ids=set(policy.protected_run_ids),
            input_snapshot_ids=set(policy.protected_input_snapshot_ids),
            effective_config_artifact_ids=set(
                policy.protected_effective_config_artifact_ids
            ),
            lineage_fragment_ids=set(policy.protected_lineage_fragment_ids),
        )

    def freeze(self) -> _ProtectedRefs:
        return _ProtectedRefs(
            manifest_ids=frozenset(self.manifest_ids),
            run_ids=frozenset(self.run_ids),
            input_snapshot_ids=frozenset(self.input_snapshot_ids),
            effective_config_artifact_ids=frozenset(self.effective_config_artifact_ids),
            lineage_fragment_ids=frozenset(self.lineage_fragment_ids),
        )


def _resolve_protected_refs(
    *,
    base_path: Path,
    policy: ControlPlaneArtifactLifecyclePolicy,
    cutoff: datetime,
) -> _ProtectedRefs:
    """Resolve explicit and live-reference protections before planning."""
    refs = _ProtectedRefAccumulator.from_policy(policy)
    _collect_manifest_protections(base_path=base_path, cutoff=cutoff, refs=refs)
    _collect_checkpoint_protections(base_path=base_path, cutoff=cutoff, refs=refs)
    _collect_lineage_protections(base_path=base_path, refs=refs)
    return refs.freeze()


def _collect_manifest_protections(
    *,
    base_path: Path,
    cutoff: datetime,
    refs: _ProtectedRefAccumulator,
) -> None:
    for manifest_path in _iter_surface_files(
        base_path, ControlPlaneArtifactSurface.RUN_MANIFEST
    ):
        if manifest_path.parent.name in _INDEX_DIR_NAMES:
            continue
        payload = _read_json_object_or_empty(manifest_path)
        if not payload or _is_payload_stale(manifest_path, payload, cutoff):
            continue
        _record_manifest_protections(path=manifest_path, payload=payload, refs=refs)


def _record_manifest_protections(
    *,
    path: Path,
    payload: dict[str, object],
    refs: _ProtectedRefAccumulator,
) -> None:
    refs.manifest_ids.add(str(payload.get("manifest_id") or path.stem))
    run_id = _optional_text(payload.get("run_id"))
    if run_id is not None:
        refs.run_ids.add(run_id)
    replay_manifest_id = _optional_text(payload.get("replay_of_manifest_id"))
    if replay_manifest_id is not None:
        refs.manifest_ids.add(replay_manifest_id)
    artifact_id = _effective_config_artifact_id(payload)
    if artifact_id is not None:
        refs.effective_config_artifact_ids.add(artifact_id)
    refs.input_snapshot_ids.update(_input_snapshot_ids(payload))


def _collect_checkpoint_protections(
    *,
    base_path: Path,
    cutoff: datetime,
    refs: _ProtectedRefAccumulator,
) -> None:
    for checkpoint_path in _iter_surface_files(
        base_path, ControlPlaneArtifactSurface.CHECKPOINT
    ):
        payload = _read_json_object_or_empty(checkpoint_path)
        if not payload or _is_payload_stale(checkpoint_path, payload, cutoff):
            continue
        _record_checkpoint_protections(payload=payload, refs=refs)


def _record_checkpoint_protections(
    *,
    payload: dict[str, object],
    refs: _ProtectedRefAccumulator,
) -> None:
    run_id = _payload_text(payload, "run_id")
    if run_id is not None:
        refs.run_ids.add(run_id)
    manifest_id = _payload_text(payload, "manifest_id")
    if manifest_id is not None:
        refs.manifest_ids.add(manifest_id)
    artifact_id = _payload_text(payload, "effective_config_artifact_id")
    if artifact_id is not None:
        refs.effective_config_artifact_ids.add(artifact_id)


def _collect_lineage_protections(
    *,
    base_path: Path,
    refs: _ProtectedRefAccumulator,
) -> None:
    manifest_ids = frozenset(refs.manifest_ids)
    run_ids = frozenset(refs.run_ids)
    for fragment_path in _lineage_fragment_files(base_path):
        payload = _read_json_object_or_empty(fragment_path)
        if not payload:
            continue
        if _manifest_or_run_is_protected(
            payload,
            manifest_ids=manifest_ids,
            run_ids=run_ids,
        ):
            refs.lineage_fragment_ids.update(_lineage_fragment_id_candidates(payload))


def _iter_artifact_refs(
    *,
    base_path: Path,
    cutoff: datetime,
    protected_refs: _ProtectedRefs,
) -> tuple[ControlPlaneArtifactRef, ...]:
    refs: list[ControlPlaneArtifactRef] = []
    for surface in ControlPlaneArtifactSurface:
        for path in _iter_surface_files(base_path, surface):
            refs.append(
                _build_artifact_ref(
                    surface=surface,
                    path=path,
                    cutoff=cutoff,
                    protected_refs=protected_refs,
                )
            )
    return tuple(refs)


def _build_artifact_ref(
    *,
    surface: ControlPlaneArtifactSurface,
    path: Path,
    cutoff: datetime,
    protected_refs: _ProtectedRefs,
) -> ControlPlaneArtifactRef:
    payload = _read_json_object_or_empty(path)
    created_at = _resolve_payload_or_file_time(path, payload)
    protected_by = _protected_by(
        surface=surface,
        path=path,
        payload=payload,
        protected_refs=protected_refs,
    )
    stale = created_at is not None and created_at < cutoff
    decision = (
        ControlPlaneArtifactLifecycleDecision.DELETE
        if stale and not protected_by
        else ControlPlaneArtifactLifecycleDecision.RETAIN
    )
    reason = _resolve_lifecycle_reason(stale=stale, protected_by=protected_by)
    return ControlPlaneArtifactRef(
        surface=surface,
        path=str(path),
        artifact_id=_artifact_id(surface=surface, path=path, payload=payload),
        decision=decision,
        reason=reason,
        created_at=created_at,
        protected_by=protected_by,
    )


def _iter_surface_files(
    base_path: Path,
    surface: ControlPlaneArtifactSurface,
) -> tuple[Path, ...]:
    surface_root = _surface_root(base_path, surface)
    if not surface_root.exists():
        return ()
    return tuple(path for path in surface_root.rglob("*") if path.is_file())


def _surface_root(base_path: Path, surface: ControlPlaneArtifactSurface) -> Path:
    if surface in {
        ControlPlaneArtifactSurface.CACHED_BRONZE,
        ControlPlaneArtifactSurface.CHECKPOINT,
    }:
        return base_path.parent / surface.value
    return base_path / surface.value


def _lineage_fragment_files(base_path: Path) -> tuple[Path, ...]:
    fragments_root = base_path / ControlPlaneArtifactSurface.LINEAGE / "fragments"
    if not fragments_root.exists():
        return ()
    return tuple(path for path in fragments_root.glob("*.json") if path.is_file())
