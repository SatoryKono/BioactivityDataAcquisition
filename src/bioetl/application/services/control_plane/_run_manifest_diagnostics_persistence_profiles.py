"""Persistence profile assembly helpers for manifest diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from bioetl.domain.control_plane.reproducibility_profiles import (
    build_lineage_closure_boundary as _build_lineage_closure_boundary,
)

__all__ = [
    "build_lineage_closure_boundary",
    "build_persistence_profile",
    "claims_payload",
    "missing_replay_ready_requirements",
    "resolve_required_profile_requirements",
]


@dataclass(frozen=True, slots=True)
class _PersistenceInputs:
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


def missing_replay_ready_requirements(
    *,
    strict_replay_execution_context_supported: bool,
    exact_replay_supported: bool,
    dependency_lock_provenance_present: bool,
    immutable_input_snapshots_present: bool,
    effective_config_artifact_present: bool,
    reproducible_semantic_output_mode: bool,
    produced_artifact_trace_present: bool,
    artifact_lineage_links_complete: bool,
) -> list[str]:
    """Return replay-ready persistence requirements missing for this run."""
    requirements = (
        (
            "strict_replay_execution_context_support",
            strict_replay_execution_context_supported,
        ),
        ("exact_replay_capability", exact_replay_supported),
        ("dependency_lock_provenance", dependency_lock_provenance_present),
        ("immutable_input_snapshots", immutable_input_snapshots_present),
        ("effective_config_artifact", effective_config_artifact_present),
        ("reproducible_semantic_output_mode", reproducible_semantic_output_mode),
        ("produced_artifact_trace", produced_artifact_trace_present),
        ("artifact_lineage_closure", artifact_lineage_links_complete),
    )
    return [name for name, present in requirements if not present]


def resolve_required_profile_requirements(
    *,
    required_profile: str,
    replay_ready_missing_requirements: list[str],
    forensic_grade_missing_requirements: list[str],
) -> tuple[str, list[str]]:
    """Return canonical required profile and its unmet requirements."""
    if required_profile == "forensic_grade":
        return required_profile, list(forensic_grade_missing_requirements)
    if required_profile == "replay_ready":
        return required_profile, list(replay_ready_missing_requirements)
    return "degraded_observable", []


def claims_payload(
    *,
    replay_ready_missing_requirements: list[str],
    forensic_grade_missing_requirements: list[str],
) -> dict[str, bool]:
    """Return profile claim booleans derived from unmet requirements."""
    return {
        "degraded_observable": True,
        "replay_ready": not replay_ready_missing_requirements,
        "forensic_grade": not forensic_grade_missing_requirements,
    }


def build_lineage_closure_boundary(
    *,
    provider: object,
    entity: object,
    contract_ref: object,
) -> dict[str, object]:
    """Return the published lineage-closure boundary for one manifested run."""
    execution_context: Literal["source", "composite"] = (
        "composite" if str(provider or "").strip() == "composite" else "source"
    )
    return _build_lineage_closure_boundary(
        provider=provider,
        entity=entity,
        contract_ref=contract_ref,
        execution_context=execution_context,
    )


def build_persistence_profile(
    *,
    base_summary: dict[str, object],
    ledger_entries_present: bool,
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    missing_link_count: int,
) -> dict[str, object]:
    """Classify the current run's persisted evidence against explicit profiles."""
    inputs = _resolve_persistence_inputs(
        base_summary=base_summary,
        artifact_refs=artifact_refs,
        lineage_fragment_ids=lineage_fragment_ids,
        missing_link_count=missing_link_count,
    )
    replay_ready_missing_requirements = missing_replay_ready_requirements(
        strict_replay_execution_context_supported=(
            inputs.strict_replay_execution_context_supported
        ),
        exact_replay_supported=inputs.exact_replay_supported,
        dependency_lock_provenance_present=inputs.dependency_lock_provenance_present,
        immutable_input_snapshots_present=inputs.immutable_input_snapshots_present,
        effective_config_artifact_present=inputs.effective_config_artifact_present,
        reproducible_semantic_output_mode=inputs.reproducible_semantic_output_mode,
        produced_artifact_trace_present=inputs.produced_artifact_trace_present,
        artifact_lineage_links_complete=inputs.artifact_lineage_links_complete,
    )
    forensic_grade_missing_requirements = _build_forensic_grade_missing_requirements(
        replay_ready_missing_requirements=replay_ready_missing_requirements,
        ledger_entries_present=ledger_entries_present,
        artifact_lineage_links_complete=inputs.artifact_lineage_links_complete,
        lineage_closure_boundary_supported=inputs.lineage_closure_boundary_supported,
        composite_resume_rich_replay_supported=(
            inputs.composite_resume_rich_replay_supported
        ),
    )
    required_profile = str(
        base_summary.get("required_persistence_profile") or "degraded_observable"
    )
    required_profile, required_profile_missing_requirements = (
        resolve_required_profile_requirements(
            required_profile=required_profile,
            replay_ready_missing_requirements=replay_ready_missing_requirements,
            forensic_grade_missing_requirements=forensic_grade_missing_requirements,
        )
    )
    attained_profile = _resolve_attained_profile(
        replay_ready_missing_requirements=replay_ready_missing_requirements,
        forensic_grade_missing_requirements=forensic_grade_missing_requirements,
    )
    composite_resume_reconstructability = _build_composite_resume_reconstructability(
        composite_execution_context=inputs.composite_execution_context,
        composite_resume_rich_replay_supported=(
            inputs.composite_resume_rich_replay_supported
        ),
    )
    return {
        "attained_profile": attained_profile,
        "required_profile": required_profile,
        "required_profile_satisfied": not required_profile_missing_requirements,
        "claims": claims_payload(
            replay_ready_missing_requirements=replay_ready_missing_requirements,
            forensic_grade_missing_requirements=forensic_grade_missing_requirements,
        ),
        "surfaces": _build_persistence_surfaces(
            inputs=inputs,
            ledger_entries_present=ledger_entries_present,
        ),
        "required_profile_missing_requirements": required_profile_missing_requirements,
        "replay_ready_missing_requirements": replay_ready_missing_requirements,
        "forensic_grade_missing_requirements": forensic_grade_missing_requirements,
        "composite_resume_reconstructability": composite_resume_reconstructability,
        "lineage_closure_boundary": inputs.lineage_closure_boundary,
    }


def _resolve_persistence_inputs(
    *,
    base_summary: dict[str, object],
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    missing_link_count: int,
) -> _PersistenceInputs:
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
    return _PersistenceInputs(
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


def _build_forensic_grade_missing_requirements(
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


def _build_persistence_surfaces(
    *,
    inputs: _PersistenceInputs,
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


def _build_composite_resume_reconstructability(
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


def _resolve_attained_profile(
    *,
    replay_ready_missing_requirements: list[str],
    forensic_grade_missing_requirements: list[str],
) -> str:
    if not forensic_grade_missing_requirements:
        return "forensic_grade"
    if not replay_ready_missing_requirements:
        return "replay_ready"
    return "degraded_observable"
