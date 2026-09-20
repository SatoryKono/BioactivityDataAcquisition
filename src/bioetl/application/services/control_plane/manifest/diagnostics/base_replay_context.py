"""Replay context assembly for base run-manifest diagnostics summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support import (
    _build_replay_projection_bundle,
)
from bioetl.application.services.control_plane.manifest.diagnostics.reproducibility_assessment import (
    _assess_manifest_reproducibility_policy,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)
from bioetl.domain.control_plane.snapshot_payloads import (
    collect_input_snapshot_content_hashes,
    collect_input_snapshot_ids,
    collect_input_snapshot_refs,
    compute_snapshot_identity_fingerprint,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
        ReplayFamilyContext,
    )


@dataclass(frozen=True, slots=True)
class _BaseSummaryReplayContext:
    """Replay- and resume-related inputs reused by base summary assembly."""

    requested_exact_replay: bool
    resume_requested: bool
    input_snapshots: list[dict[str, object]]
    input_snapshot_ids: list[str]
    input_snapshot_content_hashes: list[str]
    input_snapshot_identity_fingerprint: str | None
    snapshot_status: str
    replay_mode: str
    continuation_mode: str
    replay_capability_reason: str
    replay_readiness_verdict: str
    replay_resume_rebuild_verdict: str
    replay_next_action: str
    exact_replay_support_boundary: str
    exact_replay_blockers: list[str]
    exact_replay_eligible: bool
    replay_control_plane_state: str
    replay_state_projection: dict[str, str]
    resume_contract: dict[str, object]
    replay_family_context: ReplayFamilyContext
    replay_family_contract: dict[str, object]
    policy_assessment: ReproducibilityPolicyAssessment
    operator_replay_projection: dict[str, object]
    replay_family_contract_payload: dict[str, object]


def _resolve_base_summary_replay_context(
    manifest: RunManifest,
) -> _BaseSummaryReplayContext:
    requested_exact_replay = bool(manifest.launch_context.get("exact_replay"))
    resume_requested = bool(manifest.launch_context.get("resume"))
    input_snapshots = collect_input_snapshot_refs(manifest)
    policy_assessment = _assess_manifest_reproducibility_policy(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
    )
    replay_projection_bundle = _build_replay_projection_bundle(
        manifest=manifest,
        input_snapshots=input_snapshots,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        policy_assessment=policy_assessment,
    )
    replay_family_context = replay_projection_bundle.replay_family_context
    replay_family_contract = replay_projection_bundle.replay_family_contract
    replay_family_contract_payload = (
        replay_projection_bundle.replay_family_contract_payload
    )
    operator_replay_projection = replay_projection_bundle.operator_projection
    replay_blockers_payload = operator_replay_projection["exact_replay_blockers"]
    exact_replay_blockers = (
        [str(item) for item in replay_blockers_payload]
        if isinstance(replay_blockers_payload, list)
        else []
    )
    return _BaseSummaryReplayContext(
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        input_snapshots=input_snapshots,
        input_snapshot_ids=collect_input_snapshot_ids(input_snapshots),
        input_snapshot_content_hashes=collect_input_snapshot_content_hashes(
            input_snapshots
        ),
        input_snapshot_identity_fingerprint=compute_snapshot_identity_fingerprint(
            input_snapshots
        ),
        snapshot_status=replay_projection_bundle.snapshot_status,
        replay_mode=str(operator_replay_projection["replay_mode"]),
        continuation_mode=str(operator_replay_projection["continuation_mode"]),
        replay_capability_reason=str(
            operator_replay_projection["replay_capability_reason"]
        ),
        replay_readiness_verdict=str(
            operator_replay_projection["replay_readiness_verdict"]
        ),
        replay_resume_rebuild_verdict=str(
            operator_replay_projection["replay_resume_rebuild_verdict"]
        ),
        replay_next_action=str(operator_replay_projection["replay_next_action"]),
        exact_replay_support_boundary=str(
            operator_replay_projection["exact_replay_support_boundary"]
        ),
        exact_replay_blockers=exact_replay_blockers,
        exact_replay_eligible=replay_projection_bundle.exact_replay_eligible,
        replay_control_plane_state=replay_projection_bundle.replay_control_plane_state,
        replay_state_projection=replay_projection_bundle.replay_state_projection,
        resume_contract=replay_projection_bundle.resume_contract,
        replay_family_context=replay_family_context,
        replay_family_contract=replay_family_contract,
        policy_assessment=policy_assessment,
        operator_replay_projection=operator_replay_projection,
        replay_family_contract_payload=replay_family_contract_payload,
    )


__all__ = [
    "_BaseSummaryReplayContext",
    "_resolve_base_summary_replay_context",
]
