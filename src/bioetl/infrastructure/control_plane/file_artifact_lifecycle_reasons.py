"""Protected-reference reason helpers for artifact lifecycle planning."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.control_plane import ControlPlaneArtifactSurface
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads import (
    _content_addressed_file_snapshot_id,
    _indexed_stem,
    _lineage_fragment_id_candidates,
    _manifest_or_run_is_protected,
    _optional_text,
    _payload_text,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_types import (
    _ProtectedRefs,
)

__all__ = ["_dedupe_reasons", "_protected_by"]


def _protected_by(
    *,
    surface: ControlPlaneArtifactSurface,
    path: Path,
    payload: dict[str, object],
    protected_refs: _ProtectedRefs,
) -> tuple[str, ...]:
    if surface in {
        ControlPlaneArtifactSurface.RUN_MANIFEST,
        ControlPlaneArtifactSurface.RUN_LEDGER,
    }:
        reasons = _manifest_or_ledger_protected_reasons(
            path=path,
            payload=payload,
            protected_refs=protected_refs,
        )
        return _dedupe_reasons(reasons)
    if surface is ControlPlaneArtifactSurface.EFFECTIVE_CONFIG:
        reasons = _effective_config_protected_reasons(
            path=path,
            payload=payload,
            protected_refs=protected_refs,
        )
        return _dedupe_reasons(reasons)
    if surface is ControlPlaneArtifactSurface.LINEAGE:
        reasons = _lineage_protected_reasons(
            path=path,
            payload=payload,
            protected_refs=protected_refs,
        )
        return _dedupe_reasons(reasons)
    if surface is ControlPlaneArtifactSurface.CHECKPOINT:
        reasons = _checkpoint_protected_reasons(
            payload=payload,
            protected_refs=protected_refs,
        )
        return _dedupe_reasons(reasons)
    if surface is ControlPlaneArtifactSurface.CACHED_BRONZE:
        reasons = _cached_bronze_protected_reasons(
            path=path,
            protected_refs=protected_refs,
        )
        return _dedupe_reasons(reasons)
    return ()


def _manifest_or_ledger_protected_reasons(
    *,
    path: Path,
    payload: dict[str, object],
    protected_refs: _ProtectedRefs,
) -> list[str]:
    reasons: list[str] = []
    manifest_id = str(payload.get("manifest_id") or path.stem)
    run_id = _optional_text(payload.get("run_id"))
    if manifest_id in protected_refs.manifest_ids:
        reasons.append(f"manifest:{manifest_id}")
    if run_id in protected_refs.run_ids:
        reasons.append(f"run:{run_id}")
    indexed_run_id = _indexed_stem(path)
    if indexed_run_id in protected_refs.run_ids:
        reasons.append(f"run:{indexed_run_id}")
    return reasons


def _effective_config_protected_reasons(
    *,
    path: Path,
    payload: dict[str, object],
    protected_refs: _ProtectedRefs,
) -> list[str]:
    reasons: list[str] = []
    artifact_id = str(payload.get("artifact_id") or path.stem)
    run_id = _optional_text(payload.get("run_id")) or _indexed_stem(path)
    if artifact_id in protected_refs.effective_config_artifact_ids:
        reasons.append(f"effective_config:{artifact_id}")
    if run_id in protected_refs.run_ids:
        reasons.append(f"run:{run_id}")
    return reasons


def _lineage_protected_reasons(
    *,
    path: Path,
    payload: dict[str, object],
    protected_refs: _ProtectedRefs,
) -> list[str]:
    reasons: list[str] = []
    for fragment_id in _lineage_fragment_id_candidates(payload) or (path.stem,):
        if fragment_id in protected_refs.lineage_fragment_ids:
            reasons.append(f"lineage:{fragment_id}")
    if not _manifest_or_run_is_protected(
        payload,
        manifest_ids=protected_refs.manifest_ids,
        run_ids=protected_refs.run_ids,
    ):
        return reasons
    manifest_id = _optional_text(payload.get("manifest_id"))
    run_id = _optional_text(payload.get("run_id"))
    if manifest_id is not None:
        reasons.append(f"manifest:{manifest_id}")
    if run_id is not None:
        reasons.append(f"run:{run_id}")
    return reasons


def _checkpoint_protected_reasons(
    *,
    payload: dict[str, object],
    protected_refs: _ProtectedRefs,
) -> list[str]:
    reasons: list[str] = []
    run_id = _payload_text(payload, "run_id")
    manifest_id = _payload_text(payload, "manifest_id")
    artifact_id = _payload_text(payload, "effective_config_artifact_id")
    if run_id in protected_refs.run_ids:
        reasons.append(f"run:{run_id}")
    if manifest_id in protected_refs.manifest_ids:
        reasons.append(f"manifest:{manifest_id}")
    if artifact_id in protected_refs.effective_config_artifact_ids:
        reasons.append(f"effective_config:{artifact_id}")
    return reasons


def _cached_bronze_protected_reasons(
    *,
    path: Path,
    protected_refs: _ProtectedRefs,
) -> list[str]:
    snapshot_id = _content_addressed_file_snapshot_id(path)
    if snapshot_id in protected_refs.input_snapshot_ids:
        return [f"snapshot:{snapshot_id}"]
    return []


def _dedupe_reasons(reasons: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reasons))
