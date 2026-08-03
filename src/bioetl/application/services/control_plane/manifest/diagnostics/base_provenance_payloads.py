"""Code provenance and planned-artifact payload helpers."""

from __future__ import annotations

from bioetl.domain.control_plane import RunCodeProvenance, RunManifest


def _build_base_summary_code_provenance_payload(
    code_provenance: RunCodeProvenance,
    dependency_lock_state: object,
    code_provenance_state: dict[str, object],
) -> dict[str, object]:
    """Build the code-provenance section of the base diagnostics payload."""
    return {
        "config_hash": code_provenance.config_hash,
        "resolved_config_hash": code_provenance.resolved_config_hash,
        "effective_config_hash": code_provenance.effective_config_hash,
        "source_fingerprint": code_provenance.source_fingerprint,
        "pipeline_version": code_provenance.pipeline_version,
        "git_commit": code_provenance.git_commit,
        "source_revision_state": code_provenance.source_revision_state,
        "dependency_lock_state": dependency_lock_state,
        "code_provenance_state": code_provenance_state,
        "contract_ref": code_provenance.contract_ref,
        "contract_version": code_provenance.contract_version,
        "normalization_profile_ref": code_provenance.normalization_profile_ref,
        "normalization_profile_version": (
            code_provenance.normalization_profile_version
        ),
        "normalization_profile_hash": code_provenance.normalization_profile_hash,
        "dq_policy_ref": code_provenance.dq_policy_ref,
        "rule_bundle_version": code_provenance.rule_bundle_version,
        "dq_contract_compatibility_hash": (
            code_provenance.dq_contract_compatibility_hash
        ),
        "effective_config_artifact_id": code_provenance.effective_config_artifact_id,
    }


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
    "_build_base_summary_code_provenance_payload",
    "_build_code_provenance_state",
    "_build_planned_artifact_refs",
]
