"""Run-manifest identity graph assembly for inspection output."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.execution_identity_support import (
    build_contract_identity_anchor_fields,
    build_execution_identity_payload_from_code_provenance,
)
from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
    resolve_replay_taxonomy_projection,
)
from bioetl.domain.config.runtime import CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.normalization import compute_execution_identity_fingerprint


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
        degraded_runtime_anchor_payload = _build_degraded_runtime_anchor_payload(
            manifest
        )
        return {
            **_build_identity_graph_core(
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
        payload = build_execution_identity_payload_from_code_provenance(
            pipeline_name=manifest.pipeline_name,
            run_type=manifest.run_type.value,
            code_provenance=code_provenance,
            exact_replay=bool(manifest.launch_context.get("exact_replay")),
            input_snapshot_fingerprint=(
                snapshot_fingerprint if isinstance(snapshot_fingerprint, str) else None
            ),
            silver_filter_compatibility_mode=str(
                manifest.runtime_config.get(
                    "silver_filter_compatibility_mode",
                    CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE,
                )
            ),
        )
        return dict(payload)

    @staticmethod
    def _build_identity_graph_replay_section(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        return resolve_replay_taxonomy_projection(
            diagnostics,
            defaults={
                "replay_capability": manifest.replay_capability.value,
                "requested_exact_replay": bool(
                    manifest.launch_context.get("exact_replay")
                ),
                "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
                "exact_replay_eligible": (
                    manifest.replay_capability.value == "exact_replay_supported"
                ),
            },
        )

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
            "snapshot_status": diagnostics.get("snapshot_status"),
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


def _build_degraded_runtime_anchor_payload(
    manifest: RunManifest,
) -> dict[str, object]:
    code_provenance = manifest.code_provenance
    return {
        "manifest_id": manifest.manifest_id,
        **build_contract_identity_anchor_fields(
            code_provenance,
            include_effective_config_hash=True,
        ),
    }


def _build_identity_graph_core(
    manifest: RunManifest,
    diagnostics: dict[str, object],
    *,
    code_provenance: RunCodeProvenance,
) -> dict[str, object]:
    fallback_code_provenance_state = _fallback_code_provenance_state(code_provenance)
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
            fallback_code_provenance_state,
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
