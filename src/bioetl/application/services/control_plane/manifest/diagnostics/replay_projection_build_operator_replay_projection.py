"""Extracted _build_operator_replay_projection for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
        ReplayFamilyContext,
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
    build_context_kwargs: Callable[..., dict[str, object]],
    build_inputs: Callable[..., dict[str, object]],
    build_payload: Callable[..., dict[str, object]],
    build_taxonomy: Callable[..., dict[str, object]],
) -> dict[str, object]:
    """Return canonical operator-facing replay projection fields."""
    replay_projection_context = build_context_kwargs(
        manifest,
        input_snapshots,
        requested_exact_replay,
        resume_requested,
        policy_assessment,
        replay_family_context,
    )
    replay_inputs = build_inputs(**replay_projection_context)
    payload = build_payload(
        **replay_projection_context,
        replay_family_contract=replay_family_contract,
        replay_family_contract_payload=replay_family_contract_payload,
        replay_inputs=replay_inputs,
    )
    projection = build_taxonomy(**payload)
    parentage = payload["replay_parentage"]
    projection["replay_parentage"] = (
        dict(parentage) if isinstance(parentage, dict) else parentage
    )
    return projection
