"""Code provenance and planned-artifact payload helpers."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest


def _build_code_provenance_state(manifest: RunManifest) -> dict[str, object]:
    code_provenance = manifest.code_provenance
    blockers: list[str] = []
    if not code_provenance.git_commit:
        blockers.append("git_commit_missing")
    if str(code_provenance.source_revision_state or "").strip().lower() != "clean":
        blockers.append("source_revision_state_not_clean")
    if not code_provenance.dependency_lock_hash:
        blockers.append("dependency_lock_hash_missing")
    state: dict[str, object] = {
        "git_commit": code_provenance.git_commit,
        "source_revision_state": code_provenance.source_revision_state,
        "dependency_lock_state": (
            "present" if code_provenance.dependency_lock_hash is not None else "missing"
        ),
        "strict_code_provenance_ready": not blockers,
        "strict_code_provenance_blockers": blockers,
    }
    if code_provenance.dependency_lock_hash is not None:
        state["dependency_lock_hash"] = code_provenance.dependency_lock_hash
    return state


def _build_planned_artifact_refs(manifest: RunManifest) -> list[dict[str, object]]:
    """Return planned artifact refs in the summary payload shape."""
    return [
        {"layer": artifact.layer, "path": artifact.path}
        for artifact in manifest.planned_artifacts
    ]


__all__ = [
    "_build_code_provenance_state",
    "_build_planned_artifact_refs",
]
