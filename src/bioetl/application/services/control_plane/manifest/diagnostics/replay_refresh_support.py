"""Replay summary refresh helpers for diagnostics (ARCH-RES-04)."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.replay_projection import (
    _build_replay_projection_bundle,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_types import (
    _ReplayRefreshContext,
    _ReplayRefreshProjection,
    _ReplayRefreshSummaryUpdate,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.snapshot_materialization import (
    resolve_post_manifest_input_snapshot_materialization_mode,
)

from .replay_refresh_support_refresh_replay_summary_build_policy_assessment import (
    _refresh_replay_summary_build_policy_assessment,
)


def _build_refresh_replay_projection(
    refresh_context: _ReplayRefreshContext,
) -> _ReplayRefreshProjection:
    """Return replay-field projection after snapshot materialization refresh."""
    effective_manifest = refresh_context.effective_manifest
    policy_assessment = refresh_context.policy_assessment
    input_snapshots = refresh_context.input_snapshots
    replay_projection_bundle = _build_replay_projection_bundle(
        manifest=effective_manifest,
        input_snapshots=input_snapshots,
        requested_exact_replay=refresh_context.requested_exact_replay,
        resume_requested=refresh_context.resume_requested,
        policy_assessment=policy_assessment,
    )
    return _ReplayRefreshProjection(
        replay_payload={
            "replay_capability": policy_assessment.replay_capability.value,
            "replay_control_plane_state": replay_projection_bundle.replay_control_plane_state,
            "replay_capability_assessment": policy_assessment.to_dict(),
            **replay_projection_bundle.operator_projection,
            **replay_projection_bundle.replay_state_projection,
            "resume_contract": replay_projection_bundle.resume_contract,
        },
        exact_replay_eligible=replay_projection_bundle.exact_replay_eligible,
        replay_mode=str(replay_projection_bundle.operator_projection["replay_mode"]),
        continuation_mode=str(
            replay_projection_bundle.operator_projection["continuation_mode"]
        ),
        snapshot_status=replay_projection_bundle.snapshot_status,
        resume_contract=replay_projection_bundle.resume_contract,
    )


def _refresh_replay_summary_update_snapshot_fields(
    updated: dict[str, object],
    refresh_context: _ReplayRefreshContext,
    snapshot_status: str,
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
    updated["snapshot_status"] = snapshot_status
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
        snapshot_status=replay_projection.snapshot_status,
    )
    updated["resume_contract"] = replay_projection.resume_contract
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


__all__ = [
    "_build_replay_projection_bundle",
    "_refresh_replay_summary_from_materialized_snapshots",
]
