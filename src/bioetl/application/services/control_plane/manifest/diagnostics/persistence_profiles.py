"""Persistence profile assembly helpers for manifest diagnostics."""

from __future__ import annotations

from typing import Literal

from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profile_support import (
    build_composite_resume_reconstructability,
    build_forensic_grade_missing_requirements,
    build_persistence_surfaces,
    resolve_attained_profile,
    resolve_persistence_inputs,
)
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
    if required_profile == "degraded_observable":
        return required_profile, []
    return required_profile, ["unknown_required_persistence_profile"]


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
    inputs = resolve_persistence_inputs(
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
    forensic_grade_missing_requirements = build_forensic_grade_missing_requirements(
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
    attained_profile = resolve_attained_profile(
        replay_ready_missing_requirements=replay_ready_missing_requirements,
        forensic_grade_missing_requirements=forensic_grade_missing_requirements,
    )
    composite_resume_reconstructability = build_composite_resume_reconstructability(
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
        "surfaces": build_persistence_surfaces(
            inputs=inputs,
            ledger_entries_present=ledger_entries_present,
        ),
        "required_profile_missing_requirements": required_profile_missing_requirements,
        "replay_ready_missing_requirements": replay_ready_missing_requirements,
        "forensic_grade_missing_requirements": forensic_grade_missing_requirements,
        "composite_resume_reconstructability": composite_resume_reconstructability,
        "lineage_closure_boundary": inputs.lineage_closure_boundary,
    }
