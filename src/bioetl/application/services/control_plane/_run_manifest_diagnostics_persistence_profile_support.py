"""Private support helpers for manifest diagnostics persistence profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

__all__ = [
    "PersistenceInputs",
    "build_composite_resume_reconstructability",
    "build_forensic_grade_missing_requirements",
    "build_persistence_surfaces",
    "resolve_attained_profile",
    "resolve_persistence_inputs",
]


@dataclass(frozen=True, slots=True)
class PersistenceInputs:
    """Derived persistence inputs reused across profile assembly helpers."""

    lineage_closure_boundary: dict[str, object]
    lineage_closure_boundary_supported: bool
    effective_config_artifact_present: bool
    dependency_lock_provenance_present: bool
    immutable_input_snapshots_present: bool
    reproducible_semantic_output_mode: bool
    exact_replay_supported: bool
    strict_replay_execution_context_supported: bool
    produced_artifact_trace_present: bool
    artifact_lineage_links_complete: bool
    composite_execution_context: bool
    composite_resume_rich_replay_supported: bool


def resolve_persistence_inputs(
    *,
    base_summary: dict[str, object],
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    missing_link_count: int,
) -> PersistenceInputs:
    """Compute the derived booleans used by persistence profile assembly."""
    lineage_closure_boundary = cast(
        "dict[str, object]",
        base_summary.get("lineage_closure_boundary", {}),
    )
    replay_family_contract = cast(
        "dict[str, object]",
        base_summary.get("replay_family_contract", {}),
    )
    exact_replay_boundary = str(
        base_summary.get("exact_replay_support_boundary")
        or "snapshot_backed_source_runs_only"
    )
    replay_family_contract_name = str(
        replay_family_contract.get("contract") or ""
    ).strip()
    composite_execution_context = replay_family_contract_name.startswith("composite_")
    return PersistenceInputs(
        lineage_closure_boundary=lineage_closure_boundary,
        lineage_closure_boundary_supported=bool(
            lineage_closure_boundary.get("supported", False)
        ),
        effective_config_artifact_present=bool(
            str(base_summary.get("effective_config_artifact_id") or "").strip()
        ),
        dependency_lock_provenance_present=bool(
            str(base_summary.get("dependency_lock_hash") or "").strip()
        ),
        immutable_input_snapshots_present=bool(
            base_summary.get("input_snapshot_ids", [])
        ),
        reproducible_semantic_output_mode=not bool(
            base_summary.get("append_mode_semantic_sinks", [])
        ),
        exact_replay_supported=bool(base_summary.get("exact_replay_eligible", False)),
        strict_replay_execution_context_supported=bool(
            replay_family_contract.get(
                "strict_exact_replay_supported",
                exact_replay_boundary == "snapshot_backed_source_runs_only",
            )
        ),
        produced_artifact_trace_present=bool(artifact_refs),
        artifact_lineage_links_complete=not artifact_refs
        or (missing_link_count == 0 and bool(lineage_fragment_ids)),
        composite_execution_context=composite_execution_context,
        composite_resume_rich_replay_supported=bool(
            base_summary.get(
                "composite_resume_rich_replay_supported",
                not composite_execution_context,
            )
        ),
    )


def build_forensic_grade_missing_requirements(
    *,
    replay_ready_missing_requirements: list[str],
    ledger_entries_present: bool,
    artifact_lineage_links_complete: bool,
    lineage_closure_boundary_supported: bool,
    composite_resume_rich_replay_supported: bool,
) -> list[str]:
    """Build the forensic-grade requirement gap list from derived inputs."""
    missing = list(replay_ready_missing_requirements)
    if not ledger_entries_present:
        missing.append("run_ledger_history")
    if not artifact_lineage_links_complete:
        missing.append("artifact_lineage_links")
    if not lineage_closure_boundary_supported:
        missing.append("lineage_closure_boundary_support")
    if not composite_resume_rich_replay_supported:
        missing.append("composite_rich_replay_projection")
    return missing


def build_persistence_surfaces(
    *,
    inputs: PersistenceInputs,
    ledger_entries_present: bool,
) -> dict[str, bool]:
    """Return the persisted-evidence surface map for diagnostics output."""
    return {
        "control_plane_manifest": True,
        "effective_config_artifact": inputs.effective_config_artifact_present,
        "dependency_lock_provenance": inputs.dependency_lock_provenance_present,
        "reproducible_semantic_output_mode": inputs.reproducible_semantic_output_mode,
        "strict_replay_execution_context_support": (
            inputs.strict_replay_execution_context_supported
        ),
        "immutable_input_snapshots": inputs.immutable_input_snapshots_present,
        "exact_replay_capability": inputs.exact_replay_supported,
        "produced_artifact_trace": inputs.produced_artifact_trace_present,
        "run_ledger_history": ledger_entries_present,
        "artifact_lineage_links": inputs.artifact_lineage_links_complete,
        "lineage_closure_boundary_support": inputs.lineage_closure_boundary_supported,
    }


def build_composite_resume_reconstructability(
    *,
    composite_execution_context: bool,
    composite_resume_rich_replay_supported: bool,
) -> dict[str, object]:
    """Return the published checkpoint reconstruction scope for composite runs."""
    if composite_execution_context and composite_resume_rich_replay_supported:
        return {
            "scope": "rich_composite_resume",
            "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
            "reconstructs": [
                "state",
                "seed_completed",
                "seed_result",
                "dependency_results",
                "enrichment_results",
                "merge_result",
                "last_event_id",
                "last_event_occurred_at",
            ],
            "does_not_reconstruct": [],
            "forensic_grade_supported": True,
        }
    return {
        "scope": "coarse_grained_composite_resume",
        "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
        "reconstructs": [
            "state",
            "seed_completed",
            "merge_completed",
            "last_event_id",
            "last_event_occurred_at",
        ],
        "does_not_reconstruct": [
            "per_provider_result_maps",
            "rich_checkpoint_payloads",
        ],
        "forensic_grade_supported": composite_resume_rich_replay_supported,
    }


def resolve_attained_profile(
    *,
    replay_ready_missing_requirements: list[str],
    forensic_grade_missing_requirements: list[str],
) -> str:
    if not forensic_grade_missing_requirements:
        return "forensic_grade"
    if not replay_ready_missing_requirements:
        return "replay_ready"
    return "degraded_observable"
