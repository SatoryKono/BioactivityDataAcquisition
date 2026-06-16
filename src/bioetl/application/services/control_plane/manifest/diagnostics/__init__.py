"""Diagnostics helpers for run manifest inspection service."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import cast

from bioetl.application.services.control_plane.manifest.diagnostics.artifact_support import (
    apply_artifact_publication_closure_policy,
)
from bioetl.application.services.control_plane.manifest.diagnostics.base import (
    _build_base_summary_payload,
    _resolve_base_summary_replay_context,
)
from bioetl.application.services.control_plane.manifest.diagnostics.finalization import (
    attach_base_summary_runtime_views as _attach_base_summary_runtime_views,
)
from bioetl.application.services.control_plane.manifest.diagnostics.finalization import (
    attach_summary_reproducibility_views as _attach_summary_reproducibility_views,
)
from bioetl.application.services.control_plane.manifest.diagnostics.finalization import (
    build_final_diagnostics_summary as _build_final_diagnostics_summary,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay import (
    _build_resume_contract,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_projection import (
    _build_replay_projection_bundle,
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
from bioetl.domain.control_plane import ReplayCapability, RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    assess_reproducibility_policy,
)


@dataclass(frozen=True, slots=True)
class _ReplayRefreshContext:
    """Replay-refresh inputs reused after snapshot materialization."""

    effective_manifest: RunManifest
    policy_assessment: object
    input_snapshots: list[dict[str, object]]
    resume_requested: bool
    requested_exact_replay: bool


@dataclass(frozen=True, slots=True)
class _ReplayRefreshProjection:
    """Replay-field projection built after materialized snapshot refresh."""

    replay_payload: dict[str, object]
    exact_replay_eligible: bool
    replay_mode: str


@dataclass(frozen=True, slots=True)
class _ReplayRefreshSummaryUpdate:
    """All replay-summary updates derived after snapshot materialization."""

    payload: dict[str, object]


def _build_base_summary(
    manifest: RunManifest,
) -> dict[str, object]:
    """Build base summary from manifest code provenance."""
    replay_context = _resolve_base_summary_replay_context(manifest)
    summary = _build_base_summary_payload(manifest, replay_context)
    _attach_base_summary_runtime_views(manifest, summary)
    return summary


def build_diagnostics_summary(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Build compact operator-oriented diagnostics summary."""
    base_summary = _build_base_summary(manifest)

    if not ledger_entries:
        base_summary = apply_artifact_publication_closure_policy(base_summary)
        _attach_summary_reproducibility_views(base_summary)
        return base_summary
    return _build_final_diagnostics_summary(
        manifest=manifest,
        base_summary=base_summary,
        ledger_entries=ledger_entries,
        refresh_replay_summary_fn=_refresh_replay_summary_from_materialized_snapshots,
    )


def _refresh_replay_summary_build_policy_assessment(
    manifest: RunManifest,
    summary: dict[str, object],
    input_snapshots: list[object],
) -> _ReplayRefreshContext:
    """Build policy assessment from materialized snapshots."""
    snapshot_payloads = cast("list[dict[str, object]]", input_snapshots)
    source_refs = _build_effective_source_refs(
        manifest=manifest,
        input_snapshots=snapshot_payloads,
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
        input_snapshots=snapshot_payloads,
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
    replay_projection_bundle = _build_replay_projection_bundle(
        manifest=effective_manifest,
        input_snapshots=input_snapshots,
        requested_exact_replay=refresh_context.requested_exact_replay,
        resume_requested=refresh_context.resume_requested,
        policy_assessment=policy_assessment,
        replay_family_contract_payload={
            "post_capture_replayable_parent_supported": (
                effective_manifest.launch_context.get(
                    "post_capture_replayable_parent_supported"
                )
            )
        },
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
        cast("list[dict[str, object]]", input_snapshots)
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
        input_snapshots=cast("list[dict[str, object]]", input_snapshots),
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
    updated["resume_contract"] = _build_resume_contract(
        manifest=refresh_context.effective_manifest,
        requested_exact_replay=refresh_context.requested_exact_replay,
        resume_requested=refresh_context.resume_requested,
        policy_assessment=refresh_context.policy_assessment,
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
    refresh_context = _refresh_replay_summary_build_policy_assessment(
        manifest=manifest,
        summary=summary,
        input_snapshots=cast("list[object]", input_snapshots),
    )
    return _build_refresh_summary_update(
        summary=summary,
        refresh_context=refresh_context,
    ).payload


__all__ = ["build_diagnostics_summary"]
