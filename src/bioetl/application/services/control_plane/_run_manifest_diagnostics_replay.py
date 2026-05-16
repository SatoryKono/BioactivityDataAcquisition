"""Replay, resume, and input-snapshot helpers for manifest diagnostics."""

from __future__ import annotations

from typing import Literal

from bioetl.application.services.control_plane._run_manifest_diagnostics_base_helpers import (
    _resolve_operator_replay_mode,
    _resolve_source_posture,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_persistence import (
    build_lineage_closure_boundary,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay_helpers import (
    _append_mode_exact_replay_blockers,
    _collect_append_mode_semantic_sinks,
    _dependency_lock_exact_replay_blockers,
    _has_historical_composite_certified_snapshots,
    _has_historical_source_certified_snapshots,
    _has_live_capture_materialized_snapshots,
    _has_partial_input_snapshot_envelope,
    _is_composite_execution_context,
    _is_full_scan_idempotent_rebuild,
    _profile_exact_replay_blockers,
    _requires_resume_without_snapshot_reason,
    _resolve_applied_checkpoint_compatibility_policy,
    _resolve_exact_replay_supported_reason,
    _resolve_requested_checkpoint_compatibility_policy,
    _resolve_required_persistence_profile,
    _snapshot_exact_replay_blockers,
)
from bioetl.application.services.control_plane._run_manifest_replay_taxonomy import (
    build_replay_taxonomy_projection,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    ReplayReadinessVerdict,
    ReproducibilityPolicyAssessment,
    assess_reproducibility_policy,
    resolve_replay_readiness_verdict,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    ReproducibilityFamilyProfile,
    build_replay_family_contract,
    resolve_reproducibility_family_profile,
)


def _resolve_replay_mode(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
) -> str:
    """Resolve operator-facing replay mode from manifest intent and capability."""
    profile = _resolve_reproducibility_profile(manifest)
    if (
        requested_exact_replay
        and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        and profile.strict_exact_replay_supported
    ):
        return "exact_replay"
    if manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return "same_data_state_recovery"
    if resume_requested or manifest.replay_capability == ReplayCapability.RESUME_ONLY:
        return "resume"
    return "rebuild"


def _resolve_continuation_mode(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
) -> str:
    """Resolve the bounded continuation/replay/rebuild classification."""
    profile = _resolve_reproducibility_profile(manifest)
    if (
        requested_exact_replay
        and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        and profile.strict_exact_replay_supported
    ):
        return "exact_replay"
    if _is_full_scan_idempotent_rebuild(manifest):
        return "full_scan_idempotent_rebuild"
    if resume_requested or manifest.replay_capability == ReplayCapability.RESUME_ONLY:
        if _is_composite_execution_context(manifest):
            return "checkpoint_snapshot_plus_ledger_suffix_resume"
        return "checkpoint_snapshot_only_resume"
    return "rebuild_only"


def _resolve_replay_capability_reason(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> str:
    """Return one operator-facing explanation for replay capability."""
    profile = _resolve_reproducibility_profile(manifest)
    snapshot_envelope = policy_assessment.snapshot_envelope
    if not profile.strict_exact_replay_supported:
        return "family_outside_supported_exact_replay_boundary"
    if _collect_append_mode_semantic_sinks(manifest):
        return "append_mode_semantic_outputs_block_exact_replay"
    if _has_partial_input_snapshot_envelope(snapshot_envelope):
        return "partial_input_snapshot_envelope"
    if _has_historical_composite_certified_snapshots(input_snapshots):
        return "certified_historical_composite_snapshot_envelope_present"
    if _has_historical_source_certified_snapshots(input_snapshots):
        return "certified_historical_source_snapshot_envelope_present"
    exact_replay_reason = _resolve_exact_replay_supported_reason(
        manifest=manifest,
        input_snapshots=input_snapshots,
        snapshot_envelope=snapshot_envelope,
    )
    if exact_replay_reason is not None:
        return exact_replay_reason
    if _requires_resume_without_snapshot_reason(
        manifest=manifest,
        resume_requested=resume_requested,
    ):
        return "resume_requested_without_snapshot_backed_inputs"
    if _is_composite_execution_context(manifest):
        return "composite_snapshot_envelope_missing"
    return "immutable_input_snapshots_missing"


def _resolve_replay_occurrence_kind(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    policy_assessment: ReproducibilityPolicyAssessment,
) -> str:
    """Return the bounded replay-role classification for one manifested run."""
    replay_parentage = _build_replay_parentage(manifest)
    if bool(replay_parentage["is_exact_replay"]):
        return "exact_replay_child_run"
    if _has_historical_composite_certified_snapshots(input_snapshots):
        if policy_assessment.snapshot_envelope.full_snapshot_envelope:
            return "historical_composite_replay_certified_parent"
        return "historical_composite_certification_incomplete"
    if _has_historical_source_certified_snapshots(input_snapshots):
        if policy_assessment.snapshot_envelope.full_snapshot_envelope:
            return "historical_source_replay_certified_parent"
        return "historical_source_certification_incomplete"
    if _has_live_capture_materialized_snapshots(input_snapshots):
        if policy_assessment.snapshot_envelope.full_snapshot_envelope:
            return "materialized_replayable_parent"
        return "materialized_parent_incomplete"
    if policy_assessment.snapshot_envelope.full_snapshot_envelope:
        return "launch_time_snapshot_backed_run"
    return "ordinary_live_capture"


def _resolve_historical_live_run_upgrade_state(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    policy_assessment: ReproducibilityPolicyAssessment,
) -> str:
    """Return the bounded upgrade path for live runs lacking launch-time snapshots."""
    profile = _resolve_reproducibility_profile(manifest)
    replay_parentage = _build_replay_parentage(manifest)
    if _is_composite_execution_context(manifest) or bool(
        replay_parentage["is_exact_replay"]
    ):
        return "not_applicable"
    if _has_historical_source_certified_snapshots(input_snapshots):
        if policy_assessment.snapshot_envelope.full_snapshot_envelope:
            return "historical_source_replay_certified"
        return "historical_source_certification_incomplete"
    if _has_live_capture_materialized_snapshots(input_snapshots):
        if policy_assessment.snapshot_envelope.full_snapshot_envelope:
            return "already_materialized_replayable_parent"
        return "incomplete_materialization_evidence"
    if policy_assessment.snapshot_envelope.full_snapshot_envelope:
        return "not_needed_snapshot_backed_at_launch"
    if not profile.post_capture_replayable_parent_supported:
        return "outside_supported_boundary"
    return "awaiting_input_snapshot_published_evidence"


def _resolve_broader_historical_exact_replay_state(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    policy_assessment: ReproducibilityPolicyAssessment,
) -> str:
    """Return the bounded state for the broader certified historical tranche."""
    replay_parentage = _build_replay_parentage(manifest)
    if bool(replay_parentage["is_exact_replay"]):
        return "exact_replay_child_run"
    if _has_historical_composite_certified_snapshots(input_snapshots):
        if policy_assessment.snapshot_envelope.full_snapshot_envelope:
            return "historical_composite_replay_certified"
        return "historical_composite_certification_incomplete"
    if _has_historical_source_certified_snapshots(input_snapshots):
        if policy_assessment.snapshot_envelope.full_snapshot_envelope:
            return "historical_source_replay_certified"
        return "historical_source_certification_incomplete"
    if _has_live_capture_materialized_snapshots(input_snapshots):
        return "within_post_capture_parent_boundary"
    if policy_assessment.snapshot_envelope.full_snapshot_envelope:
        return "within_launch_time_snapshot_boundary"
    if _is_composite_execution_context(manifest):
        return "awaiting_certified_source_lineage"
    return "awaiting_historical_snapshot_certification"


def _build_replay_state_projection(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    policy_assessment: ReproducibilityPolicyAssessment,
) -> dict[str, str]:
    """Return canonical replay-state fields shared by base and refreshed views."""
    return {
        "replay_occurrence_kind": _resolve_replay_occurrence_kind(
            manifest=manifest,
            input_snapshots=input_snapshots,
            policy_assessment=policy_assessment,
        ),
        "historical_live_run_upgrade_state": (
            _resolve_historical_live_run_upgrade_state(
                manifest=manifest,
                input_snapshots=input_snapshots,
                policy_assessment=policy_assessment,
            )
        ),
        "broader_historical_exact_replay_state": (
            _resolve_broader_historical_exact_replay_state(
                manifest=manifest,
                input_snapshots=input_snapshots,
                policy_assessment=policy_assessment,
            )
        ),
        "source_posture": _resolve_source_posture(policy_assessment),
    }


def _build_operator_replay_projection(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> dict[str, object]:
    """Return canonical operator-facing replay projection fields."""
    replay_family_contract = _resolve_replay_family_contract(manifest)
    exact_replay_blockers = _resolve_exact_replay_blockers(
        manifest=manifest,
        policy_assessment=policy_assessment,
    )
    exact_replay_eligible = (
        manifest.replay_capability.value == "exact_replay_supported"
        and not exact_replay_blockers
    )
    replay_mode = _resolve_replay_mode(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
    )
    continuation_mode = _resolve_continuation_mode(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
    )
    replay_readiness_verdict = _resolve_manifest_replay_readiness_verdict(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        continuation_mode=continuation_mode,
        policy_assessment=policy_assessment,
    ).value
    return build_replay_taxonomy_projection(
        replay_capability=manifest.replay_capability.value,
        requested_exact_replay=requested_exact_replay,
        exact_replay_support_boundary=_resolve_exact_replay_support_boundary(manifest),
        replay_family_contract=replay_family_contract,
        replay_support_state=replay_family_contract.get("support_state"),
        post_capture_replayable_parent_supported=replay_family_contract.get(
            "post_capture_replayable_parent_supported"
        ),
        post_capture_replayable_parent_boundary=replay_family_contract.get(
            "post_capture_replayable_parent_boundary"
        ),
        historical_live_run_upgrade_policy=replay_family_contract.get(
            "historical_live_run_upgrade_policy"
        ),
        historical_live_run_upgrade_boundary=replay_family_contract.get(
            "historical_live_run_upgrade_boundary"
        ),
        historical_live_run_upgrade_reason=replay_family_contract.get(
            "historical_live_run_upgrade_reason"
        ),
        broader_historical_exact_replay_policy=replay_family_contract.get(
            "broader_historical_exact_replay_policy"
        ),
        broader_historical_exact_replay_boundary=replay_family_contract.get(
            "broader_historical_exact_replay_boundary"
        ),
        broader_historical_exact_replay_reason=replay_family_contract.get(
            "broader_historical_exact_replay_reason"
        ),
        broader_historical_exact_replay_state=_resolve_broader_historical_exact_replay_state(
            manifest=manifest,
            input_snapshots=input_snapshots,
            policy_assessment=policy_assessment,
        ),
        historical_live_run_upgrade_state=_resolve_historical_live_run_upgrade_state(
            manifest=manifest,
            input_snapshots=input_snapshots,
            policy_assessment=policy_assessment,
        ),
        replay_occurrence_kind=_resolve_replay_occurrence_kind(
            manifest=manifest,
            input_snapshots=input_snapshots,
            policy_assessment=policy_assessment,
        ),
        source_posture=_resolve_source_posture(policy_assessment),
        input_snapshot_missing_source_refs=list(
            policy_assessment.snapshot_envelope.missing_snapshot_source_refs
        ),
        replay_capability_reason=_resolve_replay_capability_reason(
            manifest=manifest,
            input_snapshots=input_snapshots,
            resume_requested=resume_requested,
            policy_assessment=policy_assessment,
        ),
        replay_mode=replay_mode,
        continuation_mode=continuation_mode,
        operator_replay_mode=_resolve_operator_replay_mode(
            replay_mode=replay_mode,
            continuation_mode=continuation_mode,
            replay_readiness_verdict=replay_readiness_verdict,
        ),
        exact_replay_eligible=exact_replay_eligible,
        exact_replay_blockers=exact_replay_blockers,
        replay_readiness_verdict=replay_readiness_verdict,
        append_mode_semantic_sinks=_collect_append_mode_semantic_sinks(manifest),
        resume_contract=None,
        resume_diagnostics=None,
        lineage_closure_boundary=build_lineage_closure_boundary(
            provider=manifest.provider,
            entity=manifest.entity,
            contract_ref=manifest.code_provenance.contract_ref,
        ),
    )


def _resolve_exact_replay_blockers(
    *,
    manifest: RunManifest,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> list[str]:
    """Return explicit blockers preventing exact replay eligibility."""
    profile = _resolve_reproducibility_profile(manifest)
    append_mode_sinks = _collect_append_mode_semantic_sinks(manifest)
    blockers = [
        *_profile_exact_replay_blockers(profile),
        *_append_mode_exact_replay_blockers(append_mode_sinks),
        *_snapshot_exact_replay_blockers(
            manifest=manifest,
            policy_assessment=policy_assessment,
        ),
        *_dependency_lock_exact_replay_blockers(
            manifest=manifest,
            profile=profile,
            policy_assessment=policy_assessment,
        ),
    ]
    return blockers


def _resolve_exact_replay_support_boundary(manifest: RunManifest) -> str:
    """Return the supported exact-replay boundary for one manifested run."""
    return _resolve_reproducibility_profile(manifest).exact_replay_support_boundary


def _resolve_replay_family_contract(manifest: RunManifest) -> dict[str, object]:
    """Return the canonical per-family replay contract for one manifested run."""
    execution_context: Literal["source", "composite"] = (
        "composite" if _is_composite_execution_context(manifest) else "source"
    )
    return build_replay_family_contract(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )


def _assess_manifest_reproducibility_policy(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
    replay_family_contract: dict[str, object],
) -> ReproducibilityPolicyAssessment:
    """Return the central reproducibility policy verdict for one manifest."""
    return assess_reproducibility_policy(
        source_refs=manifest.source_refs,
        required_persistence_profile=_resolve_required_persistence_profile(manifest),
        strict_exact_replay_supported=bool(
            replay_family_contract.get("strict_exact_replay_supported", False)
        ),
        exact_replay_requested=requested_exact_replay,
        resume_requested=resume_requested,
        require_full_snapshot_envelope=(
            replay_family_contract.get("contract")
            == "composite_snapshot_backed_exact_replay"
        ),
        replay_capability=manifest.replay_capability,
        run_type=manifest.run_type,
    )


def _resolve_manifest_replay_readiness_verdict(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
    continuation_mode: str,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> ReplayReadinessVerdict:
    """Return the runtime diagnostics verdict without conflating run modes."""
    lifecycle_projection_only = (
        _is_composite_execution_context(manifest)
        and "ledger_suffix" in continuation_mode
        and manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    )
    profile = _resolve_reproducibility_profile(manifest)
    runtime_blocking_gaps = list(policy_assessment.blocking_gaps)
    if (
        profile.strict_exact_replay_supported
        and (
            policy_assessment.strict_requirement_requested
            or manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        )
        and not manifest.code_provenance.dependency_lock_hash
    ):
        runtime_blocking_gaps.append("dependency_lock_provenance")
    return resolve_replay_readiness_verdict(
        replay_capability=manifest.replay_capability,
        strict_requirement_requested=policy_assessment.strict_requirement_requested,
        strict_exact_replay_supported=profile.strict_exact_replay_supported,
        blocking_gaps=tuple(dict.fromkeys(runtime_blocking_gaps)),
        exact_replay_requested=requested_exact_replay,
        resume_requested=resume_requested,
        run_type=manifest.run_type,
        debug_only=not profile.strict_exact_replay_supported,
        lifecycle_projection_only=lifecycle_projection_only,
    )


def _resolve_reproducibility_profile(
    manifest: RunManifest,
) -> ReproducibilityFamilyProfile:
    """Resolve the canonical reproducibility profile for one manifested run."""
    execution_context: Literal["source", "composite"] = (
        "composite" if _is_composite_execution_context(manifest) else "source"
    )
    return resolve_reproducibility_family_profile(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )


def _build_replay_parentage(manifest: RunManifest) -> dict[str, object]:
    """Return explicit replay ancestry for one manifested run."""
    replay_of_run_id = manifest.replay_of_run_id
    replay_of_manifest_id = manifest.replay_of_manifest_id
    return {
        "is_exact_replay": (
            replay_of_run_id is not None or replay_of_manifest_id is not None
        ),
        "replay_of_run_id": replay_of_run_id,
        "replay_of_manifest_id": replay_of_manifest_id,
    }


def _build_resume_contract(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> dict[str, object]:
    """Return the published checkpoint/resume contract for one manifested run."""
    profile = _resolve_reproducibility_profile(manifest)
    requested_policy = _resolve_requested_checkpoint_compatibility_policy(manifest)
    required_persistence_profile = policy_assessment.required_persistence_profile
    applied_policy = _resolve_applied_checkpoint_compatibility_policy(
        requested_exact_replay=requested_exact_replay,
        requested_policy=requested_policy,
        required_persistence_profile=required_persistence_profile,
    )
    strict_replay_requested = (
        requested_exact_replay
        or required_persistence_profile in STRICT_PERSISTENCE_PROFILES
    )
    is_composite = _is_composite_execution_context(manifest)
    execution_context = "composite" if is_composite else "ordinary"
    continuation_mode = _resolve_continuation_mode(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
    )
    return {
        "resume_requested": resume_requested,
        "requested_exact_replay": requested_exact_replay,
        "requested_checkpoint_compatibility_policy": requested_policy,
        "applied_checkpoint_compatibility_policy": applied_policy,
        "strict_replay_safe": (
            strict_replay_requested
            and applied_policy == "hard_fail"
            and profile.strict_exact_replay_supported
            and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
            and bool(manifest.code_provenance.dependency_lock_hash)
        ),
        "execution_context": execution_context,
        "resume_mode": (
            "checkpoint_snapshot_plus_ledger_suffix"
            if is_composite
            else "checkpoint_snapshot_only"
        ),
        "continuation_mode": continuation_mode,
        "semantic_identity_anchor": "execution_fingerprint",
        "occurrence_identity_anchor": "run_id",
    }
