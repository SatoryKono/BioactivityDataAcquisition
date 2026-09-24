"""Extracted _build_operator_replay_projection for the hotspot coverage floor (#11016)."""

from __future__ import annotations

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

from bioetl.domain.control_plane import RunManifest

from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)

def _build_operator_replay_projection(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
    replay_family_context: ReplayFamilyContext,
    replay_family_contract: dict[str, object],
    replay_family_contract_payload: dict[str, object],
) -> dict[str, object]:
    """Return canonical operator-facing replay projection fields."""
    replay_projection_context = _build_replay_projection_context_kwargs(
        manifest,
        input_snapshots,
        requested_exact_replay,
        resume_requested,
        policy_assessment,
        replay_family_context,
    )
    replay_inputs = _build_operator_replay_projection_inputs(
        **replay_projection_context
    )
    payload = _build_operator_replay_projection_payload(
        **replay_projection_context,
        replay_family_contract=replay_family_contract,
        replay_family_contract_payload=replay_family_contract_payload,
        replay_inputs=replay_inputs,
    )
    projection = build_replay_taxonomy_projection(**payload)
    parentage = payload["replay_parentage"]
    projection["replay_parentage"] = (
        dict(parentage) if isinstance(parentage, dict) else parentage
    )
    return projection
