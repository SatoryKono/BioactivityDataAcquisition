"""Replay mode and state-resolution helpers for run-manifest diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.base_replay_labels import (
    _resolve_source_posture,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.persistence_profile import (
    _resolve_reproducibility_profile,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_blockers import (
    _collect_append_mode_semantic_sinks,
    _requires_resume_without_snapshot_reason,
    _resolve_exact_replay_blockers,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_parentage import (
    _build_replay_parentage,
    _is_full_scan_idempotent_rebuild,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.snapshot_envelope import (
    _has_historical_composite_certified_snapshots,
    _has_historical_source_certified_snapshots,
    _has_live_capture_materialized_snapshots,
    _has_partial_input_snapshot_envelope,
    _resolve_exact_replay_supported_reason,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
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


__all__ = [
    "_build_replay_state_projection",
    "_resolve_broader_historical_exact_replay_state",
    "_resolve_continuation_mode",
    "_resolve_exact_replay_blockers",
    "_resolve_historical_live_run_upgrade_state",
    "_resolve_replay_capability_reason",
    "_resolve_replay_mode",
    "_resolve_replay_occurrence_kind",
]
