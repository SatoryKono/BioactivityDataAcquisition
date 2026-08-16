"""Operator-facing replay projection input and payload builders."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from bioetl.application.services.control_plane.manifest.diagnostics.operator_replay_mode import (
    _resolve_operator_replay_mode,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence import (
    build_lineage_closure_boundary,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_state import (
    _collect_append_mode_semantic_sinks,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_readiness import (
    _resolve_manifest_replay_readiness_verdict,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_state import (
    _build_replay_state_projection,
    _resolve_continuation_mode,
    _resolve_exact_replay_blockers,
    _resolve_replay_capability_reason,
    _resolve_replay_mode,
)
from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
    build_replay_taxonomy_projection as build_replay_taxonomy_projection,
    resolve_replay_next_action,
    resolve_replay_resume_rebuild_verdict,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
        ReplayFamilyContext,
    )


class _ReplayProjectionContextKwargs(TypedDict):
    """Typed shared keyword payload for replay projection builders."""

    manifest: RunManifest
    input_snapshots: list[dict[str, object]]
    requested_exact_replay: bool
    resume_requested: bool
    policy_assessment: ReproducibilityPolicyAssessment
    replay_family_context: ReplayFamilyContext


def _build_replay_projection_context_kwargs(
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
    replay_family_context: ReplayFamilyContext,
) -> _ReplayProjectionContextKwargs:
    """Return shared replay-projection context kwargs."""
    return {
        "manifest": manifest,
        "input_snapshots": input_snapshots,
        "requested_exact_replay": requested_exact_replay,
        "resume_requested": resume_requested,
        "policy_assessment": policy_assessment,
        "replay_family_context": replay_family_context,
    }


def _build_replay_state_projection_for_context(
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    policy_assessment: ReproducibilityPolicyAssessment,
    replay_family_context: ReplayFamilyContext,
) -> dict[str, str]:
    """Delegate replay-state projection construction to its canonical owner."""
    return _build_replay_state_projection(
        manifest=manifest,
        input_snapshots=input_snapshots,
        policy_assessment=policy_assessment,
        replay_family_context=replay_family_context,
    )


def _build_operator_replay_projection_inputs(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
    replay_family_context: ReplayFamilyContext,
) -> dict[str, object]:
    """Return precomputed operator replay inputs shared by projection fields."""
    exact_replay_blockers = _resolve_exact_replay_blockers(
        manifest=manifest,
        policy_assessment=policy_assessment,
        replay_family_context=replay_family_context,
    )
    replay_mode = _resolve_replay_mode(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        replay_family_context=replay_family_context,
    )
    continuation_mode = _resolve_continuation_mode(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        replay_family_context=replay_family_context,
    )
    replay_readiness_verdict = _resolve_manifest_replay_readiness_verdict(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        continuation_mode=continuation_mode,
        policy_assessment=policy_assessment,
        replay_family_context=replay_family_context,
    ).value
    replay_state_projection = _build_replay_state_projection_for_context(
        manifest, input_snapshots, policy_assessment, replay_family_context
    )
    return {
        "continuation_mode": continuation_mode,
        "exact_replay_blockers": exact_replay_blockers,
        "exact_replay_eligible": (
            manifest.replay_capability.value == "exact_replay_supported"
            and not exact_replay_blockers
        ),
        "replay_mode": replay_mode,
        "replay_readiness_verdict": replay_readiness_verdict,
        **replay_state_projection,
    }


def _build_operator_replay_projection_payload(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
    replay_family_context: ReplayFamilyContext,
    replay_family_contract: dict[str, object],
    replay_family_contract_payload: dict[str, object],
    replay_inputs: dict[str, object],
) -> dict[str, object]:
    """Return kwargs payload for the operator-facing replay taxonomy projection."""
    replay_resume_rebuild_verdict = resolve_replay_resume_rebuild_verdict(
        replay_capability=manifest.replay_capability.value,
        replay_mode=replay_inputs["replay_mode"],
        continuation_mode=replay_inputs["continuation_mode"],
        replay_readiness_verdict=replay_inputs["replay_readiness_verdict"],
    )
    return {
        "replay_capability": manifest.replay_capability.value,
        "requested_exact_replay": requested_exact_replay,
        "exact_replay_support_boundary": (
            replay_family_context.exact_replay_support_boundary
        ),
        "replay_family_contract": replay_family_contract,
        **replay_family_contract_payload,
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
            replay_family_context=replay_family_context,
        ),
        "replay_mode": replay_inputs["replay_mode"],
        "continuation_mode": replay_inputs["continuation_mode"],
        "operator_replay_mode": _resolve_operator_replay_mode(
            replay_mode=str(replay_inputs["replay_mode"]),
            continuation_mode=str(replay_inputs["continuation_mode"]),
            replay_readiness_verdict=str(replay_inputs["replay_readiness_verdict"]),
        ),
        "replay_resume_rebuild_verdict": replay_resume_rebuild_verdict,
        "replay_next_action": resolve_replay_next_action(replay_resume_rebuild_verdict),
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


__all__ = [
    "_build_operator_replay_projection_inputs",
    "_build_operator_replay_projection_payload",
    "_build_replay_projection_context_kwargs",
    "_build_replay_state_projection_for_context",
]
