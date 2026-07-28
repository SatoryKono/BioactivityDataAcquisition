"""Canonical execution-identity payload helpers owned by the manifest package."""

from __future__ import annotations

from typing import cast

from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.normalization import build_execution_identity_payload


def build_execution_identity_payload_from_code_provenance(
    *,
    pipeline_name: str,
    run_type: str,
    code_provenance: RunCodeProvenance,
    exact_replay: bool,
    input_snapshot_fingerprint: str | None,
    silver_filter_compatibility_mode: str,
) -> dict[str, object]:
    return cast(
        dict[str, object],
        build_execution_identity_payload(
            pipeline_name=pipeline_name,
            run_type=run_type,
            pipeline_version=code_provenance.pipeline_version,
            git_commit=code_provenance.git_commit,
            dependency_lock_hash=code_provenance.dependency_lock_hash,
            effective_config_hash=code_provenance.effective_config_hash,
            dq_contract_compatibility_hash=code_provenance.dq_contract_compatibility_hash,
            contract=(code_provenance.contract_ref, code_provenance.contract_version),
            normalization_profile=(
                code_provenance.normalization_profile_ref,
                code_provenance.normalization_profile_version,
                code_provenance.normalization_profile_hash,
            ),
            effective_config_artifact_id=code_provenance.effective_config_artifact_id,
            exact_replay=exact_replay,
            input_snapshot_fingerprint=input_snapshot_fingerprint,
            silver_filter_compatibility_mode=silver_filter_compatibility_mode,
        ),
    )


def build_contract_identity_anchor_fields(
    code_provenance: RunCodeProvenance,
    *,
    include_effective_config_hash: bool = False,
    include_effective_config_artifact_id: bool = True,
    include_null_values: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "contract_ref": code_provenance.contract_ref,
        "contract_version": code_provenance.contract_version,
        "normalization_profile_ref": code_provenance.normalization_profile_ref,
        "normalization_profile_version": code_provenance.normalization_profile_version,
        "normalization_profile_hash": code_provenance.normalization_profile_hash,
    }
    if include_effective_config_hash:
        payload["effective_config_hash"] = code_provenance.effective_config_hash
    if include_effective_config_artifact_id:
        payload["effective_config_artifact_id"] = (
            code_provenance.effective_config_artifact_id
        )
    if include_null_values:
        return payload
    return {key: value for key, value in payload.items() if value is not None}


def build_code_provenance_dict(
    code_provenance: RunCodeProvenance,
    *,
    include_execution_anchors: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "pipeline_version": code_provenance.pipeline_version,
        "git_commit": code_provenance.git_commit,
        "dependency_lock_hash": code_provenance.dependency_lock_hash,
        "config_hash": code_provenance.config_hash,
        "resolved_config_hash": code_provenance.resolved_config_hash,
        "effective_config_hash": code_provenance.effective_config_hash,
        "effective_config_artifact_id": code_provenance.effective_config_artifact_id,
        "contract_ref": code_provenance.contract_ref,
        "contract_version": code_provenance.contract_version,
        "contract_schema_hash": code_provenance.contract_schema_hash,
        "dq_policy_ref": code_provenance.dq_policy_ref,
        "rule_bundle_version": code_provenance.rule_bundle_version,
        "normalization_profile_ref": code_provenance.normalization_profile_ref,
        "normalization_profile_version": code_provenance.normalization_profile_version,
        "normalization_profile_hash": code_provenance.normalization_profile_hash,
        "dq_contract_compatibility_hash": code_provenance.dq_contract_compatibility_hash,
    }
    if include_execution_anchors:
        payload["source_revision_state"] = code_provenance.source_revision_state
        payload["source_fingerprint"] = code_provenance.source_fingerprint
    return {key: value for key, value in payload.items() if value is not None}


def fallback_code_provenance_state(
    code_provenance: RunCodeProvenance,
) -> dict[str, object]:
    """Build operator-facing code-provenance state for identity-graph fallbacks."""
    payload: dict[str, object] = {
        "git_commit": code_provenance.git_commit,
        "source_revision_state": code_provenance.source_revision_state,
        "dependency_lock_state": (
            "present" if code_provenance.dependency_lock_hash is not None else "missing"
        ),
        "strict_code_provenance_ready": (
            bool(code_provenance.git_commit)
            and str(code_provenance.source_revision_state or "").strip().lower()
            == "clean"
        ),
        "strict_code_provenance_blockers": [
            blocker
            for blocker, enabled in (
                ("git_commit_missing", not code_provenance.git_commit),
                (
                    "source_revision_state_not_clean",
                    str(code_provenance.source_revision_state or "").strip().lower()
                    != "clean",
                ),
            )
            if enabled
        ],
    }
    if code_provenance.dependency_lock_hash is not None:
        payload["dependency_lock_hash"] = code_provenance.dependency_lock_hash
    return payload


def build_degraded_runtime_anchor_payload(
    manifest: RunManifest,
) -> dict[str, object]:
    """Build the degraded runtime anchor payload for legacy fallback identity."""
    code_provenance = manifest.code_provenance
    return {
        "manifest_id": manifest.manifest_id,
        **build_contract_identity_anchor_fields(
            code_provenance,
            include_effective_config_hash=True,
        ),
    }


def build_identity_graph_core(
    manifest: RunManifest,
    diagnostics: dict[str, object],
    *,
    code_provenance: RunCodeProvenance,
) -> dict[str, object]:
    """Assemble the core identity-graph payload shared by fallback graphs."""
    fallback_state = fallback_code_provenance_state(code_provenance)
    payload: dict[str, object] = {
        "run_id": str(manifest.run_id),
        "manifest_id": manifest.manifest_id,
        "execution_fingerprint": manifest.execution_fingerprint,
        "config_hash": code_provenance.config_hash,
        "resolved_config_hash": code_provenance.resolved_config_hash,
        "effective_config_hash": code_provenance.effective_config_hash,
        "source_fingerprint": code_provenance.source_fingerprint,
        "git_commit": code_provenance.git_commit,
        "source_revision_state": code_provenance.source_revision_state,
        "dependency_lock_state": (
            "present" if code_provenance.dependency_lock_hash is not None else "missing"
        ),
        "code_provenance_state": diagnostics.get(
            "code_provenance_state",
            fallback_state,
        ),
        **build_contract_identity_anchor_fields(
            code_provenance,
            include_effective_config_artifact_id=False,
            include_null_values=True,
        ),
        "replay_of_run_id": diagnostics.get("replay_of_run_id"),
        "replay_of_manifest_id": diagnostics.get("replay_of_manifest_id"),
        "replay_parentage": diagnostics.get("replay_parentage"),
    }
    if code_provenance.dependency_lock_hash is not None:
        payload["dependency_lock_hash"] = code_provenance.dependency_lock_hash
    return payload


__all__ = [
    "build_code_provenance_dict",
    "build_contract_identity_anchor_fields",
    "build_degraded_runtime_anchor_payload",
    "build_execution_identity_payload_from_code_provenance",
    "build_identity_graph_core",
    "fallback_code_provenance_state",
]
