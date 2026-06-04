"""Artifact reference builders for control-plane lifecycle planning."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactReplayImpact,
    ControlPlaneArtifactSurface,
)
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_surfaces import (
    iter_surface_files,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads import (
    _artifact_id,
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


def iter_artifact_refs(
    *,
    base_path: Path,
    cutoff: datetime,
    protected_refs: _ProtectedRefs,
) -> tuple[ControlPlaneArtifactRef, ...]:
    refs: list[ControlPlaneArtifactRef] = []
    for surface in ControlPlaneArtifactSurface:
        for path in iter_surface_files(base_path, surface):
            refs.append(
                build_artifact_ref(
                    surface=surface,
                    path=path,
                    cutoff=cutoff,
                    protected_refs=protected_refs,
                )
            )
    return tuple(refs)


def build_artifact_ref(
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
    replay_impact = resolve_replay_impact(
        surface=surface,
        decision=decision,
        protected_by=protected_by,
    )
    return ControlPlaneArtifactRef(
        surface=surface,
        path=str(path),
        artifact_id=_artifact_id(surface=surface, path=path, payload=payload),
        decision=decision,
        reason=reason,
        created_at=created_at,
        protected_by=protected_by,
        replay_impact=replay_impact,
    )


def resolve_replay_impact(
    *,
    surface: ControlPlaneArtifactSurface,
    decision: ControlPlaneArtifactLifecycleDecision,
    protected_by: tuple[str, ...],
) -> ControlPlaneArtifactReplayImpact:
    """Classify whether a lifecycle action affects replay/recovery evidence."""
    if any(reason.startswith("evidence_floor:") for reason in protected_by):
        return ControlPlaneArtifactReplayImpact.STRICT_REPLAY_EVIDENCE_PROTECTED
    if protected_by:
        return ControlPlaneArtifactReplayImpact.RECOVERY_EVIDENCE_PROTECTED
    if decision is ControlPlaneArtifactLifecycleDecision.DELETE and surface in {
        ControlPlaneArtifactSurface.CACHED_BRONZE,
        ControlPlaneArtifactSurface.CHECKPOINT,
        ControlPlaneArtifactSurface.EFFECTIVE_CONFIG,
        ControlPlaneArtifactSurface.LINEAGE,
        ControlPlaneArtifactSurface.RUN_LEDGER,
        ControlPlaneArtifactSurface.RUN_MANIFEST,
    }:
        return ControlPlaneArtifactReplayImpact.UNPROTECTED_REPLAY_EVIDENCE_DELETE_CANDIDATE
    return ControlPlaneArtifactReplayImpact.NO_REPLAY_EVIDENCE
