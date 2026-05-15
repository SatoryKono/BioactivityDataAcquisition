"""Identity graph assembly for run-manifest inspection output."""

from __future__ import annotations

from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
)


class RunManifestIdentityGraphAssembler:
    """Assemble operator-facing identity graph payloads."""

    @staticmethod
    def build(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        existing = diagnostics.get("identity_graph")
        if isinstance(existing, dict):
            artifact_refs = diagnostics.get("artifact_refs")
            if isinstance(artifact_refs, list):
                existing["published_artifacts"] = [
                    artifact_ref
                    for artifact_ref in artifact_refs
                    if isinstance(artifact_ref, dict)
                ]
            return existing
        return RunManifestIdentityGraphAssembler._build_fallback_identity_graph(
            manifest,
            diagnostics,
        )

    @staticmethod
    def _build_fallback_identity_graph(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        code_provenance = manifest.code_provenance
        canonical_execution_identity = (
            RunManifestIdentityGraphAssembler._build_canonical_execution_identity(
                manifest,
                diagnostics,
            )
        )
        degraded_runtime_anchor_payload = (
            RunManifestIdentityGraphAssembler._build_degraded_runtime_anchor_payload(
                manifest
            )
        )
        return {
            **RunManifestIdentityGraphAssembler._build_identity_graph_core(
                manifest,
                diagnostics,
                code_provenance=code_provenance,
            ),
            "canonical_execution_identity": {
                "execution_fingerprint": manifest.execution_fingerprint,
                "payload": canonical_execution_identity,
            },
            "exact_replay_anchors": diagnostics.get("exact_replay_anchors", {}),
            "degraded_runtime_anchor": {
                "compatibility_scope": "legacy_fallback_only",
                "fingerprint": (
                    compute_execution_identity_fingerprint(
                        degraded_runtime_anchor_payload
                    )
                    if degraded_runtime_anchor_payload
                    else None
                ),
                "payload": degraded_runtime_anchor_payload,
            },
            **RunManifestIdentityGraphAssembler._build_identity_graph_replay_section(
                manifest,
                diagnostics,
            ),
            **RunManifestIdentityGraphAssembler._build_identity_graph_snapshot_section(
                diagnostics
            ),
            **RunManifestIdentityGraphAssembler._build_identity_graph_artifact_section(
                manifest,
                diagnostics,
            ),
        }

    @staticmethod
    def _build_canonical_execution_identity(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        code_provenance = manifest.code_provenance
        snapshot_fingerprint = diagnostics.get("input_snapshot_identity_fingerprint")
        payload = build_execution_identity_payload(
            pipeline_name=manifest.pipeline_name,
            run_type=manifest.run_type.value,
            pipeline_version=code_provenance.pipeline_version,
            git_commit=code_provenance.git_commit,
            dependency_lock_hash=code_provenance.dependency_lock_hash,
            effective_config_hash=code_provenance.effective_config_hash,
            dq_contract_compatibility_hash=(
                code_provenance.dq_contract_compatibility_hash
            ),
            contract_ref=code_provenance.contract_ref,
            contract_version=code_provenance.contract_version,
            normalization_profile_ref=code_provenance.normalization_profile_ref,
            normalization_profile_version=(
                code_provenance.normalization_profile_version
            ),
            normalization_profile_hash=code_provenance.normalization_profile_hash,
            effective_config_artifact_id=code_provenance.effective_config_artifact_id,
            exact_replay=bool(manifest.launch_context.get("exact_replay")),
            input_snapshot_fingerprint=(
                snapshot_fingerprint if isinstance(snapshot_fingerprint, str) else None
            ),
            silver_filter_compatibility_mode=str(
                manifest.runtime_config.get(
                    "silver_filter_compatibility_mode",
                    "structural_only_auto_promote",
                )
            ),
        )
        return dict(payload)

    @staticmethod
    def _build_degraded_runtime_anchor_payload(
        manifest: RunManifest,
    ) -> dict[str, object]:
        code_provenance = manifest.code_provenance
        return {
            key: value
            for key, value in {
                "manifest_id": manifest.manifest_id,
                "effective_config_hash": code_provenance.effective_config_hash,
                "contract_ref": code_provenance.contract_ref,
                "contract_version": code_provenance.contract_version,
                "normalization_profile_ref": code_provenance.normalization_profile_ref,
                "normalization_profile_version": (
                    code_provenance.normalization_profile_version
                ),
                "normalization_profile_hash": (
                    code_provenance.normalization_profile_hash
                ),
                "effective_config_artifact_id": (
                    code_provenance.effective_config_artifact_id
                ),
            }.items()
            if value is not None
        }

    @staticmethod
    def _build_identity_graph_core(
        manifest: RunManifest,
        diagnostics: dict[str, object],
        *,
        code_provenance: RunCodeProvenance,
    ) -> dict[str, object]:
        fallback_code_provenance_state = _fallback_code_provenance_state(
            code_provenance
        )
        payload: dict[str, object] = {
            "run_id": str(manifest.run_id),
            "manifest_id": manifest.manifest_id,
            "execution_fingerprint": manifest.execution_fingerprint,
            "config_hash": code_provenance.config_hash,
            "resolved_config_hash": code_provenance.resolved_config_hash,
            "effective_config_hash": code_provenance.effective_config_hash,
            "git_commit": code_provenance.git_commit,
            "source_revision_state": code_provenance.source_revision_state,
            "dependency_lock_state": (
                "present"
                if code_provenance.dependency_lock_hash is not None
                else "missing"
            ),
            "code_provenance_state": diagnostics.get(
                "code_provenance_state",
                fallback_code_provenance_state,
            ),
            "contract_ref": code_provenance.contract_ref,
            "contract_version": code_provenance.contract_version,
            "normalization_profile_ref": code_provenance.normalization_profile_ref,
            "normalization_profile_version": (
                code_provenance.normalization_profile_version
            ),
            "normalization_profile_hash": code_provenance.normalization_profile_hash,
            "replay_of_run_id": diagnostics.get("replay_of_run_id"),
            "replay_of_manifest_id": diagnostics.get("replay_of_manifest_id"),
            "replay_parentage": diagnostics.get("replay_parentage"),
        }
        if code_provenance.dependency_lock_hash is not None:
            payload["dependency_lock_hash"] = code_provenance.dependency_lock_hash
        return payload

    @staticmethod
    def _build_identity_graph_replay_section(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        replay_section = {
            "replay_capability": diagnostics.get(
                "replay_capability",
                manifest.replay_capability.value,
            ),
            "requested_exact_replay": diagnostics.get(
                "requested_exact_replay",
                bool(manifest.launch_context.get("exact_replay")),
            ),
            "exact_replay_support_boundary": diagnostics.get(
                "exact_replay_support_boundary",
                "snapshot_backed_source_runs_only",
            ),
            "replay_family_contract": diagnostics.get("replay_family_contract"),
            "replay_support_state": diagnostics.get("replay_support_state"),
            "post_capture_replayable_parent_supported": diagnostics.get(
                "post_capture_replayable_parent_supported"
            ),
            "post_capture_replayable_parent_boundary": diagnostics.get(
                "post_capture_replayable_parent_boundary"
            ),
            "historical_live_run_upgrade_policy": diagnostics.get(
                "historical_live_run_upgrade_policy"
            ),
            "historical_live_run_upgrade_boundary": diagnostics.get(
                "historical_live_run_upgrade_boundary"
            ),
            "historical_live_run_upgrade_reason": diagnostics.get(
                "historical_live_run_upgrade_reason"
            ),
            "broader_historical_exact_replay_policy": diagnostics.get(
                "broader_historical_exact_replay_policy"
            ),
            "broader_historical_exact_replay_boundary": diagnostics.get(
                "broader_historical_exact_replay_boundary"
            ),
            "broader_historical_exact_replay_reason": diagnostics.get(
                "broader_historical_exact_replay_reason"
            ),
            "broader_historical_exact_replay_state": diagnostics.get(
                "broader_historical_exact_replay_state"
            ),
            "historical_live_run_upgrade_state": diagnostics.get(
                "historical_live_run_upgrade_state"
            ),
            "replay_occurrence_kind": diagnostics.get("replay_occurrence_kind"),
            "source_posture": diagnostics.get("source_posture"),
            "input_snapshot_missing_source_refs": diagnostics.get(
                "input_snapshot_missing_source_refs",
                [],
            ),
            "replay_capability_reason": diagnostics.get("replay_capability_reason"),
            "continuation_mode": diagnostics.get("continuation_mode"),
            "exact_replay_eligible": diagnostics.get(
                "exact_replay_eligible",
                manifest.replay_capability.value == "exact_replay_supported",
            ),
            "exact_replay_blockers": diagnostics.get("exact_replay_blockers", []),
            "replay_readiness_verdict": diagnostics.get("replay_readiness_verdict"),
            "append_mode_semantic_sinks": diagnostics.get(
                "append_mode_semantic_sinks",
                [],
            ),
            "resume_contract": diagnostics.get("resume_contract"),
            "resume_diagnostics": diagnostics.get("resume_diagnostics"),
        }
        lineage_closure_boundary = diagnostics.get("lineage_closure_boundary")
        if lineage_closure_boundary is not None:
            replay_section["lineage_closure_boundary"] = lineage_closure_boundary
        return replay_section

    @staticmethod
    def _build_identity_graph_snapshot_section(
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        return {
            "input_snapshot_ids": diagnostics.get("input_snapshot_ids", []),
            "input_snapshot_content_hashes": diagnostics.get(
                "input_snapshot_content_hashes",
                [],
            ),
            "input_snapshot_identity_fingerprint": diagnostics.get(
                "input_snapshot_identity_fingerprint"
            ),
            "replay_mode": diagnostics.get("replay_mode", "rebuild"),
            "operator_replay_mode": diagnostics.get("operator_replay_mode"),
            "snapshot_status": diagnostics.get("snapshot_status"),
            "continuation_mode": diagnostics.get("continuation_mode"),
            "input_snapshot_count": diagnostics.get("input_snapshot_count", 0),
            "input_snapshots": diagnostics.get("input_snapshots", []),
        }

    @staticmethod
    def _build_identity_graph_artifact_section(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        artifact_refs = diagnostics.get("artifact_refs")
        published_artifacts = []
        if isinstance(artifact_refs, list):
            published_artifacts = [
                {
                    key: value
                    for key, value in artifact_ref.items()
                    if isinstance(artifact_ref, dict) and key != "artifact_id"
                }
                for artifact_ref in artifact_refs
                if isinstance(artifact_ref, dict)
            ]
        return {
            "planned_artifacts": [
                {"layer": artifact.layer, "path": artifact.path}
                for artifact in manifest.planned_artifacts
            ],
            "published_artifacts": published_artifacts,
            "produced_artifact_trace": diagnostics.get(
                "produced_artifact_trace",
                {},
            ),
            "occurrence_only_diagnostics": diagnostics.get(
                "occurrence_only_diagnostics", []
            ),
        }


def _fallback_code_provenance_state(
    code_provenance: RunCodeProvenance,
) -> dict[str, object]:
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
