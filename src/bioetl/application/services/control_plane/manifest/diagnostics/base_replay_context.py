"""Replay context assembly for base run-manifest diagnostics summaries."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.control_plane.manifest.diagnostics import (
    snapshot_support as _snapshot_support,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
    ReplayFamilyContext,
    build_replay_family_context,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_projection import (
    _build_replay_projection_bundle as _build_replay_projection_bundle,
)
from bioetl.application.services.control_plane.manifest.diagnostics.reproducibility_assessment import (
    _assess_manifest_reproducibility_policy,
)
from bioetl.application.services.control_plane.manifest.diagnostics.resume_contract import (
    _build_resume_contract,
)
from bioetl.application.services.control_plane.manifest.replay_family_contract_payload import (
    build_replay_family_contract_payload as _build_replay_family_contract_payload,
)
from bioetl.application.services.control_plane.manifest.replay_family_contract_payload import (
    build_replay_family_contract_payload as build_replay_family_contract_payload,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)

_collect_input_snapshot_content_hashes = (
    _snapshot_support.collect_input_snapshot_content_hashes
)
_collect_input_snapshot_ids = _snapshot_support.collect_input_snapshot_ids
_collect_input_snapshot_refs = _snapshot_support.collect_input_snapshot_refs
_compute_input_snapshot_identity_fingerprint = (
    _snapshot_support.compute_input_snapshot_identity_fingerprint
)


@dataclass(frozen=True, slots=True)
class _BaseSummaryReplayContext:
    """Replay- and resume-related inputs reused by base summary assembly."""

    requested_exact_replay: bool
    resume_requested: bool
    input_snapshots: list[dict[str, object]]
    replay_mode: str
    continuation_mode: str
    replay_capability_reason: str
    replay_readiness_verdict: str
    replay_resume_rebuild_verdict: str
    replay_next_action: str
    exact_replay_support_boundary: str
    exact_replay_blockers: list[str]
    resume_contract: dict[str, object]
    replay_family_context: ReplayFamilyContext
    replay_family_contract: dict[str, object]
    policy_assessment: ReproducibilityPolicyAssessment
    operator_replay_projection: dict[str, object]


def _resolve_base_summary_replay_context(
    manifest: RunManifest,
) -> _BaseSummaryReplayContext:
    requested_exact_replay = bool(manifest.launch_context.get("exact_replay"))
    resume_requested = bool(manifest.launch_context.get("resume"))
    input_snapshots = _collect_input_snapshot_refs(manifest)
    replay_family_context = build_replay_family_context(manifest)
    replay_family_contract = replay_family_context.replay_family_contract
    policy_assessment = _assess_manifest_reproducibility_policy(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        replay_family_context=replay_family_context,
    )
    replay_projection_bundle = _build_replay_projection_bundle(
        manifest=manifest,
        input_snapshots=input_snapshots,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        policy_assessment=policy_assessment,
        replay_family_context=replay_family_context,
        replay_family_contract=replay_family_contract,
        replay_family_contract_payload=_build_replay_family_contract_payload(
            replay_family_contract
        ),
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
        resume_contract=_build_resume_contract(
            manifest=manifest,
            requested_exact_replay=requested_exact_replay,
            resume_requested=resume_requested,
            continuation_mode=str(operator_replay_projection["continuation_mode"]),
            policy_assessment=policy_assessment,
            replay_family_context=replay_family_context,
        ),
        replay_family_context=replay_family_context,
        replay_family_contract=replay_family_contract,
        policy_assessment=policy_assessment,
        operator_replay_projection=operator_replay_projection,
    )


__all__ = [
    "_BaseSummaryReplayContext",
    "_resolve_base_summary_replay_context",
]
