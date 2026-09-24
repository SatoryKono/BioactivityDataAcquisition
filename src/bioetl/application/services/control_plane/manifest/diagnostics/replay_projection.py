"""Operator-facing replay projection assembly for manifest diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
    ReplayFamilyContext,
    build_replay_family_context,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_projection_payload import (
    _build_operator_replay_projection_inputs,
    _build_operator_replay_projection_payload,
    _build_replay_projection_context_kwargs,
    _build_replay_state_projection_for_context,
    build_replay_taxonomy_projection,
)
from bioetl.application.services.control_plane.manifest.diagnostics.resume_contract import (
    _build_resume_contract,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_projection_build_operator_replay_projection import _build_operator_replay_projection


@dataclass(frozen=True, slots=True)
class _ReplayProjectionBundle:
    """Shared replay projection bundle reused across diagnostics surfaces."""

    operator_projection: dict[str, object]
    replay_state_projection: dict[str, str]
    replay_control_plane_state: str
    exact_replay_eligible: bool
    snapshot_status: str
    resume_contract: dict[str, object]
    replay_family_context: ReplayFamilyContext
    replay_family_contract: dict[str, object]
    replay_family_contract_payload: dict[str, object]




def _resolve_snapshot_status(
    *,
    input_snapshots: list[dict[str, object]],
    exact_replay_eligible: bool,
    replay_mode: str,
) -> str:
    """Return operator-facing completeness of immutable input snapshots."""
    if not input_snapshots:
        return "none"
    if exact_replay_eligible or replay_mode in {
        "exact_replay",
        "same_data_state_recovery",
    }:
        return "full"
    return "partial"


def _resolve_replay_control_plane_state(
    *,
    manifest: RunManifest,
    replay_state_projection: dict[str, str],
    replay_family_contract_payload: dict[str, object],
) -> str:
    """Return the bounded machine-readable replay state for one manifest."""
    if manifest.replay_capability.value == "exact_replay_supported":
        return "exact_replay_supported"
    if manifest.replay_capability.value == "resume_only":
        return "resume_only"
    if (
        replay_family_contract_payload.get("post_capture_replayable_parent_supported")
        is True
        and replay_state_projection.get("historical_live_run_upgrade_state")
        == "awaiting_input_snapshot_published_evidence"
    ):
        return "post_capture_parent_candidate"
    return "rebuild_only"


def _build_replay_projection_bundle(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
    replay_family_context: ReplayFamilyContext | None = None,
    replay_family_contract: dict[str, object] | None = None,
    replay_family_contract_payload: dict[str, object] | None = None,
) -> _ReplayProjectionBundle:
    """Assemble the canonical replay projection bundle for diagnostics callers."""
    if replay_family_context is None:
        replay_family_context = build_replay_family_context(manifest)
    if replay_family_contract is None:
        replay_family_contract = replay_family_context.replay_family_contract
    if replay_family_contract_payload is None:
        replay_family_contract_payload = (
            replay_family_context.replay_family_contract_payload
        )
    replay_projection_context = _build_replay_projection_context_kwargs(
        manifest,
        input_snapshots,
        requested_exact_replay,
        resume_requested,
        policy_assessment,
        replay_family_context,
    )
    operator_projection = _build_operator_replay_projection(
        **replay_projection_context,
        replay_family_contract=replay_family_contract,
        replay_family_contract_payload=replay_family_contract_payload,
    )
    replay_state_projection = _build_replay_state_projection_for_context(
        manifest, input_snapshots, policy_assessment, replay_family_context
    )
    exact_replay_eligible = bool(
        operator_projection.get("exact_replay_eligible", False)
    )
    replay_mode = str(operator_projection.get("replay_mode", ""))
    continuation_mode = str(operator_projection.get("continuation_mode", ""))
    return _ReplayProjectionBundle(
        operator_projection=operator_projection,
        replay_state_projection=replay_state_projection,
        replay_control_plane_state=_resolve_replay_control_plane_state(
            manifest=manifest,
            replay_state_projection=replay_state_projection,
            replay_family_contract_payload=replay_family_contract_payload,
        ),
        exact_replay_eligible=exact_replay_eligible,
        snapshot_status=_resolve_snapshot_status(
            input_snapshots=input_snapshots,
            exact_replay_eligible=exact_replay_eligible,
            replay_mode=replay_mode,
        ),
        resume_contract=_build_resume_contract(
            manifest=manifest,
            requested_exact_replay=requested_exact_replay,
            resume_requested=resume_requested,
            continuation_mode=continuation_mode,
            policy_assessment=policy_assessment,
            replay_family_context=replay_family_context,
        ),
        replay_family_context=replay_family_context,
        replay_family_contract=replay_family_contract,
        replay_family_contract_payload=replay_family_contract_payload,
    )


__all__ = [
    "_build_operator_replay_projection",
    "_build_replay_projection_bundle",
    "_resolve_replay_control_plane_state",
    "_resolve_snapshot_status",
]
