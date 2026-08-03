"""Source-class provenance builders for effective-config artifacts."""

from __future__ import annotations

from bioetl.domain.control_plane.effective_config_artifact import (
    SourceClassProvenance,
)

__all__ = ["build_source_class_provenance"]


def build_source_class_provenance() -> tuple[SourceClassProvenance, ...]:
    return (
        SourceClassProvenance(
            source_class="config_file",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.source_refs[*]",
            anchor_field="source_hash",
            notes=(
                "File-backed YAML config sources use canonical semantic source_hash "
                "values for identity; raw_source_hash preserves forensic byte-level "
                "integrity when available."
            ),
        ),
        SourceClassProvenance(
            source_class="cli_override",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.runtime_overrides.cli_overrides",
            anchor_field="override_hash",
            notes="CLI overrides are collapsed into the runtime override hash.",
        ),
        SourceClassProvenance(
            source_class="env_override",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.runtime_overrides.env_overrides",
            anchor_field="override_hash",
            notes=(
                "Explicit allowlisted environment overrides are materialized into "
                "env_overrides and collapsed into the runtime override hash; "
                "non-allowlisted semantic env overrides are rejected during "
                "artifact creation."
            ),
        ),
        SourceClassProvenance(
            source_class="runtime_adjustment",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.runtime_overrides.runtime_adjustments",
            anchor_field="override_hash",
            notes="Runtime adjustments are collapsed into the runtime override hash.",
        ),
        SourceClassProvenance(
            source_class="dq_policy_contract",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.dq_policy_refs[*]",
            anchor_field="policy_hash",
            notes=(
                "DQ policy anchors are persisted when DQ policy config participates "
                "in materialization."
            ),
        ),
        SourceClassProvenance(
            source_class="immutable_input_snapshot",
            provenance_status="external_anchor",
            artifact_surface="run_manifest.source_refs[*].input_snapshots[*]",
            anchor_field="content_hash",
            notes=(
                "Immutable Bronze input snapshots are anchored in the run manifest "
                "rather than the effective-config artifact."
            ),
        ),
        SourceClassProvenance(
            source_class="implicit_process_environment",
            provenance_status="policy_excluded",
            artifact_surface="semantic_artifact.execution_environment",
            anchor_field="environment_hash",
            notes=(
                "Ambient process environment is excluded by policy unless it is "
                "explicitly materialized through runtime_overrides.env; the "
                "execution_environment surface anchors that exclusion policy and "
                "the set of materialized semantic env overrides."
            ),
        ),
    )
