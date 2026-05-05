"""Internal mixins for run-manifest inspection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
)

if TYPE_CHECKING:
    from .run_manifest_inspection_models import RunManifestDiffEntry

_OCCURRENCE_ONLY_DIFF_FIELDS = frozenset({"manifest_id", "run_id", "created_at"})


class RunManifestInspectionIdentityGraphMixin:
    """Build operator-facing identity graph payloads for inspection output."""

    @staticmethod
    def _build_identity_graph(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        """Return one operator-facing run identity graph payload."""
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

        return RunManifestInspectionIdentityGraphMixin._build_fallback_identity_graph(
            manifest,
            diagnostics,
        )

    @staticmethod
    def _build_fallback_identity_graph(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        """Build identity graph when diagnostics did not already provide one."""
        mixin = RunManifestInspectionIdentityGraphMixin
        code_provenance = manifest.code_provenance
        canonical_execution_identity = mixin._build_canonical_execution_identity(
            manifest,
            diagnostics,
        )
        degraded_runtime_anchor_payload = mixin._build_degraded_runtime_anchor_payload(
            manifest
        )
        return {
            **mixin._build_identity_graph_core(
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
            **mixin._build_identity_graph_replay_section(
                manifest,
                diagnostics,
            ),
            **mixin._build_identity_graph_snapshot_section(diagnostics),
            **mixin._build_identity_graph_artifact_section(
                manifest,
                diagnostics,
            ),
        }

    @staticmethod
    def _build_canonical_execution_identity(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        """Return the canonical execution identity payload for inspection output."""
        code_provenance = manifest.code_provenance
        snapshot_fingerprint = diagnostics.get("input_snapshot_identity_fingerprint")
        payload = build_execution_identity_payload(
            pipeline_name=manifest.pipeline_name,
            run_type=manifest.run_type.value,
            pipeline_version=code_provenance.pipeline_version,
            git_commit=code_provenance.git_commit,
            effective_config_hash=code_provenance.effective_config_hash,
            dq_contract_compatibility_hash=(
                code_provenance.dq_contract_compatibility_hash
            ),
            contract_ref=code_provenance.contract_ref,
            contract_version=code_provenance.contract_version,
            effective_config_artifact_id=code_provenance.effective_config_artifact_id,
            exact_replay=bool(manifest.launch_context.get("exact_replay")),
            input_snapshot_fingerprint=(
                snapshot_fingerprint if isinstance(snapshot_fingerprint, str) else None
            ),
        )
        return dict(payload)

    @staticmethod
    def _build_degraded_runtime_anchor_payload(
        manifest: RunManifest,
    ) -> dict[str, object]:
        """Return the fallback runtime anchor payload for inspection output."""
        code_provenance = manifest.code_provenance
        return {
            key: value
            for key, value in {
                "manifest_id": manifest.manifest_id,
                "effective_config_hash": code_provenance.effective_config_hash,
                "contract_ref": code_provenance.contract_ref,
                "contract_version": code_provenance.contract_version,
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
        """Return the provenance and contract section of the identity graph."""
        fallback_code_provenance_state: dict[str, object] = {
            "git_commit": code_provenance.git_commit,
            "source_revision_state": code_provenance.source_revision_state,
            "dependency_lock_state": (
                "present"
                if code_provenance.dependency_lock_hash is not None
                else "missing"
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
            fallback_code_provenance_state["dependency_lock_hash"] = (
                code_provenance.dependency_lock_hash
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
        """Return replay/resume-related identity graph fields."""
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
            "replay_capability_reason": diagnostics.get("replay_capability_reason"),
            "continuation_mode": diagnostics.get("continuation_mode"),
            "exact_replay_eligible": diagnostics.get(
                "exact_replay_eligible",
                manifest.replay_capability.value == "exact_replay_supported",
            ),
            "exact_replay_blockers": diagnostics.get("exact_replay_blockers", []),
            "append_mode_semantic_sinks": diagnostics.get(
                "append_mode_semantic_sinks",
                [],
            ),
            "resume_contract": diagnostics.get("resume_contract"),
            "resume_diagnostics": diagnostics.get("resume_diagnostics"),
        }
        lineage_closure_boundary = diagnostics.get("lineage_closure_boundary")
        if lineage_closure_boundary is not None and bool(
            diagnostics.get("total_events")
        ):
            replay_section["lineage_closure_boundary"] = lineage_closure_boundary
        return replay_section

    @staticmethod
    def _build_identity_graph_snapshot_section(
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        """Return input-snapshot and replay-mode fields for the identity graph."""
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
        """Return artifact and occurrence-only sections for the identity graph."""
        return {
            "planned_artifacts": [
                {"layer": artifact.layer, "path": artifact.path}
                for artifact in manifest.planned_artifacts
            ],
            "published_artifacts": [],
            "produced_artifact_trace": diagnostics.get(
                "produced_artifact_trace",
                {},
            ),
            "occurrence_only_diagnostics": diagnostics.get(
                "occurrence_only_diagnostics", []
            ),
        }


class RunManifestInspectionDiffClassificationMixin:
    """Classify manifest diffs into operator-facing semantic buckets."""

    @staticmethod
    def _classify_manifest_diff(
        *,
        left_manifest: RunManifest,
        right_manifest: RunManifest,
        differences: tuple[RunManifestDiffEntry, ...],
    ) -> dict[str, object]:
        """Classify a manifest diff into occurrence-only vs semantic drift."""
        diff_fields = tuple(entry.field for entry in differences)
        if not diff_fields:
            return {
                "classification": "identical",
                "semantic_equivalent": True,
                "occurrence_only": False,
                "occurrence_difference_fields": (),
                "semantic_difference_fields": (),
                "noncanonical_difference_fields": (),
                "replay_relationship": "none",
            }

        occurrence_difference_fields = tuple(
            field for field in diff_fields if field in _OCCURRENCE_ONLY_DIFF_FIELDS
        )
        non_occurrence_fields = tuple(
            field for field in diff_fields if field not in _OCCURRENCE_ONLY_DIFF_FIELDS
        )
        semantic_equivalent = (
            left_manifest.execution_fingerprint == right_manifest.execution_fingerprint
        )
        replay_relationship = (
            RunManifestInspectionDiffClassificationMixin._resolve_replay_relationship(
                left_manifest=left_manifest,
                right_manifest=right_manifest,
            )
        )
        if semantic_equivalent:
            return RunManifestInspectionDiffClassificationMixin._semantic_equivalent_diff_payload(
                occurrence_difference_fields=occurrence_difference_fields,
                non_occurrence_fields=non_occurrence_fields,
                replay_relationship=replay_relationship,
            )
        return {
            "classification": "semantic_drift",
            "semantic_equivalent": False,
            "occurrence_only": False,
            "occurrence_difference_fields": occurrence_difference_fields,
            "semantic_difference_fields": non_occurrence_fields or diff_fields,
            "noncanonical_difference_fields": (),
            "replay_relationship": replay_relationship,
        }

    @staticmethod
    def _semantic_equivalent_diff_payload(
        *,
        occurrence_difference_fields: tuple[str, ...],
        non_occurrence_fields: tuple[str, ...],
        replay_relationship: str,
    ) -> dict[str, object]:
        """Return the diff payload for semantic-equivalent manifest pairs."""
        if not non_occurrence_fields:
            return {
                "classification": "occurrence_only",
                "semantic_equivalent": True,
                "occurrence_only": True,
                "occurrence_difference_fields": occurrence_difference_fields,
                "semantic_difference_fields": (),
                "noncanonical_difference_fields": (),
                "replay_relationship": replay_relationship,
            }
        return {
            "classification": "semantic_equivalent_with_noncanonical_differences",
            "semantic_equivalent": True,
            "occurrence_only": False,
            "occurrence_difference_fields": occurrence_difference_fields,
            "semantic_difference_fields": (),
            "noncanonical_difference_fields": non_occurrence_fields,
            "replay_relationship": replay_relationship,
        }

    @staticmethod
    def _manifest_replays_other(
        *,
        manifest: RunManifest,
        other: RunManifest,
    ) -> bool:
        """Return whether one manifest explicitly replays the other."""
        return (
            manifest.replay_of_manifest_id == other.manifest_id
            or manifest.replay_of_run_id == str(other.run_id)
        )

    @staticmethod
    def _resolve_replay_relationship(
        *,
        left_manifest: RunManifest,
        right_manifest: RunManifest,
    ) -> str:
        """Classify explicit replay ancestry separately from semantic equality."""
        left_replays_right = (
            RunManifestInspectionDiffClassificationMixin._manifest_replays_other(
                manifest=left_manifest,
                other=right_manifest,
            )
        )
        right_replays_left = (
            RunManifestInspectionDiffClassificationMixin._manifest_replays_other(
                manifest=right_manifest,
                other=left_manifest,
            )
        )
        if left_replays_right and right_replays_left:
            return "mutual_replay_cycle"
        if left_replays_right:
            return "left_is_exact_replay_of_right"
        if right_replays_left:
            return "right_is_exact_replay_of_left"
        if (
            left_manifest.replay_of_manifest_id is not None
            or left_manifest.replay_of_run_id is not None
            or right_manifest.replay_of_manifest_id is not None
            or right_manifest.replay_of_run_id is not None
        ):
            return "external_replay_parentage_present"
        return "none"
