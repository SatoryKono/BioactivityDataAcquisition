"""Diagnostics helpers for run manifest inspection service."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import cast

from bioetl.application.services.control_plane._run_manifest_diagnostics_base import (
    _build_base_summary_payload,
    _resolve_base_summary_replay_context,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_base_helpers import (
    _resolve_snapshot_status,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_ledger import (
    _process_ledger_entries,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_main_helpers import (
    _build_unified_reproducibility_diagnostics,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay import (
    _build_operator_replay_projection,
    _build_replay_state_projection,
    _build_resume_contract,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_snapshot_support import (
    merge_ledger_input_snapshots_into_summary,
    resolve_post_manifest_input_snapshot_materialization_mode,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_source_refs import (
    _attach_rich_composite_replay_support,
    _build_effective_source_refs,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_summary import (
    _build_final_summary,
    _build_runtime_views,
    _FinalSummaryRequest,
    _RuntimeViewsRequest,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
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


def _attach_base_summary_runtime_views(
    manifest: RunManifest,
    summary: dict[str, object],
) -> None:
    """Attach persistence, alert, and scoring overlays to base summary."""
    persistence_profile, alert_signals, next_steps = _build_runtime_views(
        _RuntimeViewsRequest(
            manifest=manifest,
            summary=summary,
            ledger_entries_present=False,
            artifact_refs=[],
            lineage_fragment_ids=set(),
            missing_link_count=0,
            latest_status=None,
            dq_signal_present=False,
            cross_validation_signal_present=False,
        )
    )
    summary["persistence_profile"] = persistence_profile
    summary["alert_signals"] = alert_signals
    summary["next_steps"] = next_steps
    _attach_summary_reproducibility_views(summary)


def _attach_summary_reproducibility_views(summary: dict[str, object]) -> None:
    """Attach canonical reproducibility diagnostics and score overlays."""
    summary["reproducibility_diagnostics"] = _build_unified_reproducibility_diagnostics(
        summary
    )
    summary["reproducibility_audit_score"] = build_reproducibility_audit_scoring(
        summary
    )


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
        return base_summary
    base_summary = merge_ledger_input_snapshots_into_summary(
        base_summary,
        ledger_entries,
    )
    base_summary = _refresh_replay_summary_from_materialized_snapshots(
        manifest=manifest,
        summary=base_summary,
    )
    base_summary = _attach_rich_composite_replay_support(
        base_summary,
        ledger_entries,
    )

    (
        family_counter,
        type_counter,
        artifact_refs,
        lineage_fragment_ids,
        dq_rule_ids,
        dq_dispositions,
        dq_report_paths,
        dq_violation_kinds,
        cross_validation_rule_ids,
        cross_validation_config_paths,
        cross_validation_quarantine_policies,
        cross_validation_replay_contracts,
        occurrence_only_diagnostic_scopes,
        dq_signal_present,
        cross_validation_signal_present,
        missing_link_count,
        correlation_anchor_gaps,
        resume_diagnostics,
    ) = _process_ledger_entries(ledger_entries)

    final_summary = _build_final_summary(
        _FinalSummaryRequest(
            manifest=manifest,
            base_summary=base_summary,
            ledger_entries=ledger_entries,
            family_counter=family_counter,
            type_counter=type_counter,
            artifact_refs=artifact_refs,
            lineage_fragment_ids=lineage_fragment_ids,
            dq_rule_ids=dq_rule_ids,
            dq_dispositions=dq_dispositions,
            dq_report_paths=dq_report_paths,
            dq_violation_kinds=dq_violation_kinds,
            cross_validation_rule_ids=cross_validation_rule_ids,
            cross_validation_config_paths=cross_validation_config_paths,
            cross_validation_quarantine_policies=(cross_validation_quarantine_policies),
            cross_validation_replay_contracts=cross_validation_replay_contracts,
            occurrence_only_diagnostic_scopes=occurrence_only_diagnostic_scopes,
            dq_signal_present=dq_signal_present,
            cross_validation_signal_present=cross_validation_signal_present,
            missing_link_count=missing_link_count,
            correlation_anchor_gaps=correlation_anchor_gaps,
            resume_diagnostics=resume_diagnostics,
        )
    )
    _attach_summary_reproducibility_views(final_summary)
    return final_summary


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
    operator_replay_projection = _build_operator_replay_projection(
        manifest=effective_manifest,
        input_snapshots=input_snapshots,
        requested_exact_replay=refresh_context.requested_exact_replay,
        resume_requested=refresh_context.resume_requested,
        policy_assessment=policy_assessment,
    )
    return _ReplayRefreshProjection(
        replay_payload={
            "replay_capability": policy_assessment.replay_capability.value,
            "replay_capability_assessment": policy_assessment.to_dict(),
            **operator_replay_projection,
            **_build_replay_state_projection(
                manifest=effective_manifest,
                input_snapshots=input_snapshots,
                policy_assessment=policy_assessment,
            ),
        },
        exact_replay_eligible=bool(operator_replay_projection["exact_replay_eligible"]),
        replay_mode=str(operator_replay_projection["replay_mode"]),
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
    updated = dict(summary)
    replay_projection = _build_refresh_replay_projection(refresh_context)
    updated.update(replay_projection.replay_payload)
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
    return updated


__all__ = ["build_diagnostics_summary"]
