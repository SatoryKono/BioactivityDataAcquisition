"""Checkpoint artifact candidate collection for lifecycle planning."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bioetl.domain.control_plane import (
    ControlPlaneArtifactResolutionIssue,
    ControlPlaneArtifactResolutionIssueCode,
    ControlPlaneArtifactSurface,
    RunManifest,
)
from bioetl.domain.types import JsonDict, RunID


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


def _append_checkpoint_history_dir(
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]],
    checkpoint_root: Path,
    manifest: RunManifest,
    history_run_dir: Callable[[Path, str, RunID], Path],
) -> None:
    run_dir = history_run_dir(checkpoint_root, manifest.pipeline_name, manifest.run_id)
    if not run_dir.is_dir():
        return
    for path in run_dir.iterdir():
        if path.is_file():
            candidates.append((ControlPlaneArtifactSurface.CHECKPOINT, path))


def _append_checkpoint_manifest_index(
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]],
    issues: list[ControlPlaneArtifactResolutionIssue],
    checkpoint_root: Path,
    manifest: RunManifest,
    *,
    history_path_from_manifest_index: Callable[[Path, str], Path],
    manifest_index_path: Callable[[Path, str], Path],
    read_json_file: Callable[[Path], JsonDict],
) -> None:
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
