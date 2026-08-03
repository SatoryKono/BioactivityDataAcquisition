"""Replay summary refresh helpers for diagnostics (ARCH-RES-04)."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from bioetl.application.services.control_plane.manifest.diagnostics.replay import (
    _build_resume_contract,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
    build_replay_family_context,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_projection import (
    _build_replay_projection_bundle,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_types import (
    _ReplayRefreshContext,
    _ReplayRefreshProjection,
    _ReplayRefreshSummaryUpdate,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_materialization import (
    resolve_post_manifest_input_snapshot_materialization_mode,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_status import (
    _resolve_snapshot_status,
)
from bioetl.application.services.control_plane.manifest.diagnostics.source_refs import (
    _build_effective_source_refs,
)
from bioetl.application.services.control_plane.manifest.replay_family_contract_payload import (
    build_replay_family_contract_payload as _build_replay_family_contract_payload,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    assess_reproducibility_policy,
)


def _refresh_replay_summary_build_policy_assessment(
    manifest: RunManifest,
    summary: dict[str, object],
    input_snapshots: list[dict[str, object]],
) -> _ReplayRefreshContext:
    """Build policy assessment from materialized snapshots."""
    source_refs = _build_effective_source_refs(
        manifest=manifest,
        input_snapshots=input_snapshots,
    )
    replay_assessment_seed = cast(
        "dict[str, object]",
        summary.get("replay_capability_assessment", {}),
    )
    strict_exact_replay_supported = bool(
        replay_assessment_seed.get("strict_exact_replay_supported", False)
    )
    requested_exact_replay = bool(summary.get("requested_exact_replay", False))
    resume_requested = bool(manifest.launch_context.get("resume"))
    replay_capability_seed: ReplayCapability | None = None
    if any(source_ref.input_snapshots for source_ref in source_refs):
        replay_capability_seed = ReplayCapability.EXACT_REPLAY_SUPPORTED
    policy_assessment = assess_reproducibility_policy(
        source_refs=source_refs,
        required_persistence_profile=summary.get(
            "required_persistence_profile",
            "degraded_observable",
        ),
        strict_exact_replay_supported=strict_exact_replay_supported,
        exact_replay_requested=requested_exact_replay,
        resume_requested=resume_requested,
        replay_capability=replay_capability_seed,
        run_type=manifest.run_type.value,
        debug_only=False,
        lifecycle_projection_only=False,
    )
    effective_manifest = replace(
        manifest,
        replay_capability=policy_assessment.replay_capability,
        source_refs=source_refs,
    )
    return _ReplayRefreshContext(
        effective_manifest=effective_manifest,
        policy_assessment=policy_assessment,
        input_snapshots=input_snapshots,
        resume_requested=resume_requested,
        requested_exact_replay=requested_exact_replay,
    )


def _build_refresh_replay_projection(
    refresh_context: _ReplayRefreshContext,
) -> _ReplayRefreshProjection:
    """Return replay-field projection after snapshot materialization refresh."""
    effective_manifest = refresh_context.effective_manifest
    policy_assessment = refresh_context.policy_assessment
    input_snapshots = refresh_context.input_snapshots
    replay_family_context = build_replay_family_context(effective_manifest)
    replay_family_contract = replay_family_context.replay_family_contract
    replay_family_contract_payload = _build_replay_family_contract_payload(
        replay_family_contract
    )
    replay_projection_bundle = _build_replay_projection_bundle(
        manifest=effective_manifest,
        input_snapshots=input_snapshots,
        requested_exact_replay=refresh_context.requested_exact_replay,
        resume_requested=refresh_context.resume_requested,
        policy_assessment=policy_assessment,
        replay_family_context=replay_family_context,
        replay_family_contract=replay_family_contract,
        replay_family_contract_payload=replay_family_contract_payload,
    )
    return _ReplayRefreshProjection(
        replay_payload={
            "replay_capability": policy_assessment.replay_capability.value,
            "replay_control_plane_state": replay_projection_bundle.replay_control_plane_state,
            "replay_capability_assessment": policy_assessment.to_dict(),
            **replay_projection_bundle.operator_projection,
            **replay_projection_bundle.replay_state_projection,
        },
        exact_replay_eligible=replay_projection_bundle.exact_replay_eligible,
        replay_mode=str(replay_projection_bundle.operator_projection["replay_mode"]),
        continuation_mode=str(
            replay_projection_bundle.operator_projection["continuation_mode"]
        ),
    )


def _refresh_replay_summary_update_snapshot_fields(
    updated: dict[str, object],
    refresh_context: _ReplayRefreshContext,
    exact_replay_eligible: bool,
    replay_mode: str,
) -> dict[str, object]:
    """Update snapshot-related fields in summary."""
    input_snapshots = refresh_context.input_snapshots
    policy_assessment = refresh_context.policy_assessment
    materialization_mode = resolve_post_manifest_input_snapshot_materialization_mode(
        input_snapshots
    )
    if materialization_mode is not None:
        updated["input_snapshot_materialization_mode"] = materialization_mode
        if materialization_mode == "historical_source_snapshot_certified":
            updated["source_posture"] = "historical_source_replay_certified_envelope"
        elif materialization_mode == ("historical_composite_replay_envelope_certified"):
            updated["source_posture"] = "historical_composite_replay_certified_envelope"
        elif materialization_mode == "live_capture_snapshot_materialized":
            updated["source_posture"] = "live_capture_snapshot_materialized"
    updated["input_snapshot_missing_source_refs"] = list(
        policy_assessment.snapshot_envelope.missing_snapshot_source_refs
    )
    updated["snapshot_status"] = _resolve_snapshot_status(
        input_snapshots=input_snapshots,
        exact_replay_eligible=exact_replay_eligible,
        replay_mode=replay_mode,
    )
    return updated


def _build_refresh_summary_update(
    *,
    summary: dict[str, object],
    refresh_context: _ReplayRefreshContext,
) -> _ReplayRefreshSummaryUpdate:
    """Build the full summary update after replay refresh and snapshot merge."""
    updated = dict(summary)
    replay_projection = _build_refresh_replay_projection(refresh_context)
    updated.update(replay_projection.replay_payload)
    if bool(summary.get("composite_resume_rich_replay_supported")) and (
        updated.get("replay_readiness_verdict") == "lifecycle_projection_only"
    ):
        updated["replay_readiness_verdict"] = "resume_compatible"
        if updated.get("operator_replay_mode") == "Lifecycle Projection":
            updated["operator_replay_mode"] = "Resume"
    updated = _refresh_replay_summary_update_snapshot_fields(
        updated=updated,
        refresh_context=refresh_context,
        exact_replay_eligible=replay_projection.exact_replay_eligible,
        replay_mode=replay_projection.replay_mode,
    )
    replay_family_context = build_replay_family_context(
        refresh_context.effective_manifest
    )
    updated["resume_contract"] = _build_resume_contract(
        manifest=refresh_context.effective_manifest,
        requested_exact_replay=refresh_context.requested_exact_replay,
        resume_requested=refresh_context.resume_requested,
        continuation_mode=replay_projection.continuation_mode,
        policy_assessment=refresh_context.policy_assessment,
        replay_family_context=replay_family_context,
    )
    return _ReplayRefreshSummaryUpdate(payload=updated)


def _refresh_replay_summary_from_materialized_snapshots(
    *,
    manifest: RunManifest,
    summary: dict[str, object],
) -> dict[str, object]:
    """Recompute replay policy after ledger-derived snapshots are merged."""
    input_snapshots = summary.get("input_snapshots")
    if not isinstance(input_snapshots, list) or not input_snapshots:
        return summary
    snapshot_payloads = [
        {str(key): value for key, value in item.items()}
        for item in input_snapshots
        if isinstance(item, dict)
    ]
    if not snapshot_payloads:
        return summary
    refresh_context = _refresh_replay_summary_build_policy_assessment(
        manifest=manifest,
        summary=summary,
        input_snapshots=snapshot_payloads,
    )
    return _build_refresh_summary_update(
        summary=summary,
        refresh_context=refresh_context,
    ).payload


__all__ = ["_refresh_replay_summary_from_materialized_snapshots"]

__all__ = ["_refresh_replay_summary_from_materialized_snapshots"]
