"""Artifact reference builders for control-plane lifecycle planning."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactReplayImpact,
    ControlPlaneArtifactResolutionIssue,
    ControlPlaneArtifactResolutionIssueCode,
    ControlPlaneArtifactSurface,
    RunManifest,
)
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_surfaces import (
    iter_surface_files,
)
from bioetl.infrastructure.control_plane._file_lineage_index import (
    LineageIndexCorruptionError,
    load_fragment_ids,
    stable_key_filename,
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

_BRONZE_URI_PREFIX = "bronze://"


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


def iter_artifact_refs_for_manifest(
    *,
    base_path: Path,
    cutoff: datetime,
    protected_refs: _ProtectedRefs,
    manifest: RunManifest,
) -> tuple[ControlPlaneArtifactRef, ...]:
    """Build a bounded plan for one manifest without walking the full catalog."""
    artifacts, _issues = plan_manifest_artifact_refs(
        base_path=base_path,
        cutoff=cutoff,
        protected_refs=protected_refs,
        manifest=manifest,
    )
    return artifacts


def plan_manifest_artifact_refs(
    *,
    base_path: Path,
    cutoff: datetime,
    protected_refs: _ProtectedRefs,
    manifest: RunManifest,
) -> tuple[
    tuple[ControlPlaneArtifactRef, ...],
    tuple[ControlPlaneArtifactResolutionIssue, ...],
]:
    """Resolve selected-run artifacts and typed index/URI issues."""
    issues: list[ControlPlaneArtifactResolutionIssue] = []
    refs = [
        build_artifact_ref(
            surface=surface,
            path=path,
            cutoff=cutoff,
            protected_refs=protected_refs,
        )
        for surface, path in _manifest_candidate_paths(base_path, manifest, issues)
        if path.is_file()
    ]
    return (
        tuple(sorted(refs, key=lambda ref: (ref.surface.value, ref.path))),
        tuple(issues),
    )


def _manifest_candidate_paths(
    base_path: Path,
    manifest: RunManifest,
    issues: list[ControlPlaneArtifactResolutionIssue],
) -> list[tuple[ControlPlaneArtifactSurface, Path]]:
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]] = [
        (
            ControlPlaneArtifactSurface.RUN_MANIFEST,
            base_path / "run_manifest" / f"{manifest.manifest_id}.json",
        ),
        (
            ControlPlaneArtifactSurface.RUN_MANIFEST,
            base_path
            / "run_manifest"
            / f"{manifest.manifest_id}.contract-evidence.json",
        ),
        (
            ControlPlaneArtifactSurface.RUN_LEDGER,
            base_path / "run_ledger" / f"{manifest.manifest_id}.jsonl",
        ),
    ]
    _append_effective_config_candidate(candidates, base_path, manifest)
    _append_lineage_candidates(candidates, issues, base_path, manifest)
    _append_checkpoint_candidates(candidates, issues, base_path, manifest)
    _append_cached_bronze_candidates(candidates, issues, base_path, manifest)
    return candidates


def _append_effective_config_candidate(
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]],
    base_path: Path,
    manifest: RunManifest,
) -> None:
    config_id = manifest.code_provenance.effective_config_artifact_id
    if not config_id:
        return
    candidates.append(
        (
            ControlPlaneArtifactSurface.EFFECTIVE_CONFIG,
            base_path / "effective_config" / f"{config_id}.json",
        )
    )


def _append_lineage_candidates(
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]],
    issues: list[ControlPlaneArtifactResolutionIssue],
    base_path: Path,
    manifest: RunManifest,
) -> None:
    lineage_index = (
        base_path
        / "lineage"
        / "_by_manifest_id"
        / f"{stable_key_filename(manifest.manifest_id)}.jsonl"
    )
    if not lineage_index.is_file():
        issues.append(
            _resolution_issue(
                ControlPlaneArtifactResolutionIssueCode.LINEAGE_INDEX_MISSING,
                ControlPlaneArtifactSurface.LINEAGE,
                "Lineage manifest index is not recorded for this manifest.",
            )
        )
        return
    candidates.append((ControlPlaneArtifactSurface.LINEAGE, lineage_index))
    try:
        fragment_ids = load_fragment_ids(lineage_index, key=manifest.manifest_id)
    except (OSError, LineageIndexCorruptionError, ValueError):
        issues.append(
            _resolution_issue(
                ControlPlaneArtifactResolutionIssueCode.LINEAGE_INDEX_CORRUPT,
                ControlPlaneArtifactSurface.LINEAGE,
                "Lineage manifest index is corrupt for this manifest.",
            )
        )
        return
    fragments_root = base_path / "lineage" / "fragments"
    for fragment_id in fragment_ids:
        hashed = fragments_root / f"{stable_key_filename(fragment_id)}.json"
        paths = [hashed]
        if fragment_id and "/" not in fragment_id and "\\" not in fragment_id:
            paths.append(fragments_root / f"{fragment_id}.json")
        for path in paths:
            if path.is_file():
                candidates.append((ControlPlaneArtifactSurface.LINEAGE, path))


def _append_checkpoint_candidates(
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]],
    issues: list[ControlPlaneArtifactResolutionIssue],
    base_path: Path,
    manifest: RunManifest,
) -> None:
    from bioetl.infrastructure.checkpoint._local_checkpoint_io import (
        history_path_from_manifest_index,
        history_run_dir,
        manifest_index_path,
        read_json_file,
    )

    checkpoint_root = base_path.parent / "checkpoints"
    if not checkpoint_root.exists():
        issues.append(
            _resolution_issue(
                ControlPlaneArtifactResolutionIssueCode.CHECKPOINT_INDEX_MISSING,
                ControlPlaneArtifactSurface.CHECKPOINT,
                "Checkpoint manifest index is not recorded for this manifest.",
            )
        )
        return
    latest = checkpoint_root / f"{manifest.pipeline_name}.json"
    if latest.is_file():
        try:
            latest_payload = read_json_file(latest)
        except (OSError, ValueError, TypeError):
            latest_payload = {}
        if str(latest_payload.get("run_id") or "") == str(manifest.run_id):
            candidates.append((ControlPlaneArtifactSurface.CHECKPOINT, latest))
    run_dir = history_run_dir(checkpoint_root, manifest.pipeline_name, manifest.run_id)
    if run_dir.is_dir():
        for path in run_dir.iterdir():
            if path.is_file():
                candidates.append((ControlPlaneArtifactSurface.CHECKPOINT, path))
    index_path = manifest_index_path(checkpoint_root, manifest.manifest_id)
    if not index_path.is_file():
        issues.append(
            _resolution_issue(
                ControlPlaneArtifactResolutionIssueCode.CHECKPOINT_INDEX_MISSING,
                ControlPlaneArtifactSurface.CHECKPOINT,
                "Checkpoint manifest index is not recorded for this manifest.",
            )
        )
        return
    candidates.append((ControlPlaneArtifactSurface.CHECKPOINT, index_path))
    try:
        payload = read_json_file(index_path)
    except (OSError, ValueError, TypeError, UnicodeError):
        issues.append(
            _resolution_issue(
                ControlPlaneArtifactResolutionIssueCode.CHECKPOINT_INDEX_CORRUPT,
                ControlPlaneArtifactSurface.CHECKPOINT,
                "Checkpoint manifest index is corrupt for this manifest.",
            )
        )
        return
    history_rel = payload.get("history_path") if isinstance(payload, dict) else None
    if not isinstance(history_rel, str) or not history_rel.strip():
        issues.append(
            _resolution_issue(
                ControlPlaneArtifactResolutionIssueCode.CHECKPOINT_INDEX_CORRUPT,
                ControlPlaneArtifactSurface.CHECKPOINT,
                "Checkpoint manifest index is missing history_path.",
            )
        )
        return
    history_path = history_path_from_manifest_index(
        checkpoint_root, history_rel.strip()
    )
    if history_path.is_file():
        candidates.append((ControlPlaneArtifactSurface.CHECKPOINT, history_path))


def _append_cached_bronze_candidates(
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]],
    issues: list[ControlPlaneArtifactResolutionIssue],
    base_path: Path,
    manifest: RunManifest,
) -> None:
    bronze_root = base_path.parent / "bronze"
    seen: set[Path] = set()
    for source in manifest.source_refs:
        for snapshot in source.input_snapshots:
            uri = snapshot.immutable_uri
            if uri is None or not str(uri).strip():
                issues.append(
                    _resolution_issue(
                        ControlPlaneArtifactResolutionIssueCode.SNAPSHOT_URI_NOT_RECORDED,
                        ControlPlaneArtifactSurface.CACHED_BRONZE,
                        "Input snapshot "
                        f"'{snapshot.snapshot_id}' has no immutable_uri.",
                    )
                )
                continue
            path = resolve_bronze_uri(bronze_root, str(uri).strip())
            if path is None:
                issues.append(
                    _resolution_issue(
                        ControlPlaneArtifactResolutionIssueCode.SNAPSHOT_URI_NOT_RECORDED,
                        ControlPlaneArtifactSurface.CACHED_BRONZE,
                        "Input snapshot "
                        f"'{snapshot.snapshot_id}' immutable_uri is not a usable "
                        "bronze:// location.",
                    )
                )
                continue
            if path in seen:
                continue
            seen.add(path)
            candidates.append((ControlPlaneArtifactSurface.CACHED_BRONZE, path))
    for artifact in manifest.planned_artifacts:
        layer = str(getattr(artifact, "layer", "") or "").strip().lower()
        raw_path = str(getattr(artifact, "path", "") or "").strip()
        if layer not in {"bronze", "cached_bronze"} or not raw_path:
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = (base_path.parent / path).resolve()
        if path in seen:
            continue
        seen.add(path)
        candidates.append((ControlPlaneArtifactSurface.CACHED_BRONZE, path))


def resolve_bronze_uri(bronze_root: Path, immutable_uri: str) -> Path | None:
    """Resolve a `bronze://` URI to a path under the Bronze root."""
    if not immutable_uri.startswith(_BRONZE_URI_PREFIX):
        return None
    relative = immutable_uri[len(_BRONZE_URI_PREFIX) :].strip()
    if not relative:
        return None
    parts = Path(relative.replace("\\", "/")).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    return bronze_root.joinpath(*parts)


def _resolution_issue(
    code: ControlPlaneArtifactResolutionIssueCode,
    surface: ControlPlaneArtifactSurface,
    detail: str,
) -> ControlPlaneArtifactResolutionIssue:
    return ControlPlaneArtifactResolutionIssue(
        code=code,
        surface=surface,
        detail=detail,
    )


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
