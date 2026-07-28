"""Operator-facing replay projection assembly for manifest diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.diagnostics.replay_projection_payload import (
    _build_operator_replay_projection_inputs,
    _build_operator_replay_projection_payload,
    _build_replay_projection_context_kwargs,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_state import (
    _build_replay_state_projection,
)
from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
    build_replay_taxonomy_projection,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
        ReplayFamilyContext,
    )


@dataclass(frozen=True, slots=True)
class _ReplayProjectionBundle:
    """Shared replay projection bundle reused across diagnostics surfaces."""

    operator_projection: dict[str, object]
    replay_state_projection: dict[str, str]
    replay_control_plane_state: str
    exact_replay_eligible: bool


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
    return build_replay_taxonomy_projection(
        **_build_operator_replay_projection_payload(
            **replay_projection_context,
            replay_family_contract=replay_family_contract,
            replay_family_contract_payload=replay_family_contract_payload,
            replay_inputs=replay_inputs,
        )
    )


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
    replay_family_context: ReplayFamilyContext,
    replay_family_contract: dict[str, object],
    replay_family_contract_payload: dict[str, object],
) -> _ReplayProjectionBundle:
    """Assemble the canonical replay projection bundle for diagnostics callers."""
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
    replay_state_projection = _build_replay_state_projection(
        manifest=manifest,
        input_snapshots=input_snapshots,
        policy_assessment=policy_assessment,
        replay_family_context=replay_family_context,
    )
    return _ReplayProjectionBundle(
        operator_projection=operator_projection,
        replay_state_projection=replay_state_projection,
        replay_control_plane_state=_resolve_replay_control_plane_state(
            manifest=manifest,
            replay_state_projection=replay_state_projection,
            replay_family_contract_payload=replay_family_contract_payload,
        ),
        exact_replay_eligible=bool(
            operator_projection.get("exact_replay_eligible", False)
        ),
    )


__all__ = [
    "_build_operator_replay_projection",
    "_build_replay_projection_bundle",
    "_resolve_replay_control_plane_state",
]
