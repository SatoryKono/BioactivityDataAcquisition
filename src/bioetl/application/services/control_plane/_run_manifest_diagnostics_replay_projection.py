"""Operator-facing replay projection assembly for manifest diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane._run_manifest_diagnostics_base_helpers import (
    _resolve_operator_replay_mode,
    _resolve_source_posture,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_persistence import (
    build_lineage_closure_boundary,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay import (
    _resolve_broader_historical_exact_replay_state,
    _resolve_continuation_mode,
    _resolve_exact_replay_blockers,
    _resolve_historical_live_run_upgrade_state,
    _resolve_manifest_replay_readiness_verdict,
    _resolve_replay_capability_reason,
    _resolve_replay_mode,
    _resolve_replay_occurrence_kind,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay_helpers import (
    _collect_append_mode_semantic_sinks,
    _resolve_exact_replay_support_boundary,
    _resolve_replay_family_contract,
)
from bioetl.application.services.control_plane._run_manifest_replay_taxonomy import (
    build_replay_taxonomy_projection,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)


def _build_operator_replay_projection_inputs(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> dict[str, object]:
    """Return precomputed operator replay inputs shared by projection fields."""
    exact_replay_blockers = _resolve_exact_replay_blockers(
        manifest=manifest,
        policy_assessment=policy_assessment,
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
    return {
        "continuation_mode": continuation_mode,
        "exact_replay_blockers": exact_replay_blockers,
        "exact_replay_eligible": (
            manifest.replay_capability.value == "exact_replay_supported"
            and not exact_replay_blockers
        ),
        "historical_live_run_upgrade_state": (
            _resolve_historical_live_run_upgrade_state(
                manifest=manifest,
                input_snapshots=input_snapshots,
                policy_assessment=policy_assessment,
            )
        ),
        "replay_mode": replay_mode,
        "replay_occurrence_kind": _resolve_replay_occurrence_kind(
            manifest=manifest,
            input_snapshots=input_snapshots,
            policy_assessment=policy_assessment,
        ),
        "replay_readiness_verdict": replay_readiness_verdict,
        "broader_historical_exact_replay_state": (
            _resolve_broader_historical_exact_replay_state(
                manifest=manifest,
                input_snapshots=input_snapshots,
                policy_assessment=policy_assessment,
            )
        ),
        "source_posture": _resolve_source_posture(policy_assessment),
    }


def _build_operator_replay_projection_payload(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
    replay_family_contract: dict[str, object],
    replay_inputs: dict[str, object],
) -> dict[str, object]:
    """Return kwargs payload for the operator-facing replay taxonomy projection."""
    return {
        "replay_capability": manifest.replay_capability.value,
        "requested_exact_replay": requested_exact_replay,
        "exact_replay_support_boundary": _resolve_exact_replay_support_boundary(
            manifest
        ),
        "replay_family_contract": replay_family_contract,
        "replay_support_state": replay_family_contract.get("support_state"),
        "post_capture_replayable_parent_supported": replay_family_contract.get(
            "post_capture_replayable_parent_supported"
        ),
        "post_capture_replayable_parent_boundary": replay_family_contract.get(
            "post_capture_replayable_parent_boundary"
        ),
        "historical_live_run_upgrade_policy": replay_family_contract.get(
            "historical_live_run_upgrade_policy"
        ),
        "historical_live_run_upgrade_boundary": replay_family_contract.get(
            "historical_live_run_upgrade_boundary"
        ),
        "historical_live_run_upgrade_reason": replay_family_contract.get(
            "historical_live_run_upgrade_reason"
        ),
        "broader_historical_exact_replay_policy": replay_family_contract.get(
            "broader_historical_exact_replay_policy"
        ),
        "broader_historical_exact_replay_boundary": replay_family_contract.get(
            "broader_historical_exact_replay_boundary"
        ),
        "broader_historical_exact_replay_reason": replay_family_contract.get(
            "broader_historical_exact_replay_reason"
        ),
        "broader_historical_exact_replay_state": replay_inputs[
            "broader_historical_exact_replay_state"
        ],
        "historical_live_run_upgrade_state": replay_inputs[
            "historical_live_run_upgrade_state"
        ],
        "replay_occurrence_kind": replay_inputs["replay_occurrence_kind"],
        "source_posture": replay_inputs["source_posture"],
        "input_snapshot_missing_source_refs": list(
            policy_assessment.snapshot_envelope.missing_snapshot_source_refs
        ),
        "replay_capability_reason": _resolve_replay_capability_reason(
            manifest=manifest,
            input_snapshots=input_snapshots,
            resume_requested=resume_requested,
            policy_assessment=policy_assessment,
        ),
        "replay_mode": replay_inputs["replay_mode"],
        "continuation_mode": replay_inputs["continuation_mode"],
        "operator_replay_mode": _resolve_operator_replay_mode(
            replay_mode=str(replay_inputs["replay_mode"]),
            continuation_mode=str(replay_inputs["continuation_mode"]),
            replay_readiness_verdict=str(replay_inputs["replay_readiness_verdict"]),
        ),
        "exact_replay_eligible": replay_inputs["exact_replay_eligible"],
        "exact_replay_blockers": replay_inputs["exact_replay_blockers"],
        "replay_readiness_verdict": replay_inputs["replay_readiness_verdict"],
        "append_mode_semantic_sinks": _collect_append_mode_semantic_sinks(manifest),
        "resume_contract": None,
        "resume_diagnostics": None,
        "lineage_closure_boundary": build_lineage_closure_boundary(
            provider=manifest.provider,
            entity=manifest.entity,
            contract_ref=manifest.code_provenance.contract_ref,
        ),
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
    replay_inputs = _build_operator_replay_projection_inputs(
        manifest=manifest,
        input_snapshots=input_snapshots,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        policy_assessment=policy_assessment,
    )
    return build_replay_taxonomy_projection(
        **_build_operator_replay_projection_payload(
            manifest=manifest,
            input_snapshots=input_snapshots,
            requested_exact_replay=requested_exact_replay,
            resume_requested=resume_requested,
            policy_assessment=policy_assessment,
            replay_family_contract=replay_family_contract,
            replay_inputs=replay_inputs,
        )
    )


__all__ = ["_build_operator_replay_projection"]
