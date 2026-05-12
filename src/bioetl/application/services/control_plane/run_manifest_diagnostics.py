"""Diagnostics helpers for run manifest inspection service."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import cast

from bioetl.application.services.control_plane._run_manifest_diagnostics_base import (
    _build_base_summary_payload,
    _resolve_base_summary_replay_context,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_base_helpers import (
    _resolve_operator_replay_mode,
    _resolve_snapshot_status,
    _resolve_source_posture,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_ledger import (
    _process_ledger_entries,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_main_helpers import (
    _build_unified_reproducibility_diagnostics,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_persistence import (
    build_alert_signals,
    build_next_steps,
    build_persistence_profile,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay import (
    _build_resume_contract,
    _is_composite_execution_context,
    _resolve_broader_historical_exact_replay_state,
    _resolve_continuation_mode,
    _resolve_exact_replay_blockers,
    _resolve_historical_live_run_upgrade_state,
    _resolve_replay_capability_reason,
    _resolve_replay_mode,
    _resolve_replay_occurrence_kind,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_snapshot_support import (
    merge_ledger_input_snapshots_into_summary,
    resolve_post_manifest_input_snapshot_materialization_mode,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_summary import (
    _build_final_summary,
    _FinalSummaryRequest,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    assess_reproducibility_policy,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
)


def _attach_base_summary_runtime_views(
    manifest: RunManifest,
    summary: dict[str, object],
) -> None:
    """Attach persistence, alert, and scoring overlays to base summary."""
    persistence_profile = build_persistence_profile(
        base_summary=summary,
        ledger_entries_present=False,
        artifact_refs=[],
        lineage_fragment_ids=set(),
        missing_link_count=0,
    )
    summary["persistence_profile"] = persistence_profile
    summary["alert_signals"] = build_alert_signals(
        latest_status=None,
        artifact_refs=[],
        lineage_fragment_ids=set(),
        missing_link_count=0,
        composite_resume_reconstructability_gap=_is_composite_execution_context(
            manifest
        ),
        dq_signal_present=False,
        cross_validation_signal_present=False,
        required_persistence_profile_missing_requirements=cast(
            list[str],
            persistence_profile.get("required_profile_missing_requirements", []),
        ),
        replay_ready_missing_requirements=cast(
            list[str],
            persistence_profile.get("replay_ready_missing_requirements", []),
        ),
        forensic_grade_missing_requirements=cast(
            list[str],
            persistence_profile.get("forensic_grade_missing_requirements", []),
        ),
    )
    summary["next_steps"] = build_next_steps(
        cast(dict[str, bool], summary["alert_signals"])
    )
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
    final_summary["reproducibility_diagnostics"] = (
        _build_unified_reproducibility_diagnostics(final_summary)
    )
    return final_summary


def _refresh_replay_summary_build_policy_assessment(
    manifest: RunManifest,
    summary: dict[str, object],
    input_snapshots: list[object],
) -> tuple[RunManifest, object, bool]:
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
    return effective_manifest, policy_assessment, resume_requested


def _refresh_replay_summary_update_replay_fields(
    updated: dict[str, object],
    effective_manifest: RunManifest,
    policy_assessment: object,
    input_snapshots: list[object],
    resume_requested: bool,
    requested_exact_replay: bool,
) -> tuple[dict[str, object], bool, str, str]:
    """Update replay-related fields in summary."""
    updated["replay_capability"] = policy_assessment.replay_capability.value
    updated["replay_capability_assessment"] = policy_assessment.to_dict()
    updated["replay_capability_reason"] = _resolve_replay_capability_reason(
        manifest=effective_manifest,
        input_snapshots=cast("list[dict[str, object]]", input_snapshots),
        resume_requested=resume_requested,
        policy_assessment=policy_assessment,
    )
    updated["exact_replay_blockers"] = _resolve_exact_replay_blockers(
        manifest=effective_manifest,
        policy_assessment=policy_assessment,
    )
    exact_replay_eligible = (
        effective_manifest.replay_capability.value == "exact_replay_supported"
        and not updated["exact_replay_blockers"]
    )
    updated["exact_replay_eligible"] = exact_replay_eligible
    updated["replay_readiness_verdict"] = (
        policy_assessment.replay_readiness_verdict.value
    )
    replay_mode = _resolve_replay_mode(
        manifest=effective_manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
    )
    continuation_mode = _resolve_continuation_mode(
        manifest=effective_manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
    )
    updated["replay_mode"] = replay_mode
    updated["continuation_mode"] = continuation_mode
    updated["operator_replay_mode"] = _resolve_operator_replay_mode(
        replay_mode=replay_mode,
        continuation_mode=continuation_mode,
        replay_readiness_verdict=policy_assessment.replay_readiness_verdict.value,
    )
    updated["replay_occurrence_kind"] = _resolve_replay_occurrence_kind(
        manifest=effective_manifest,
        input_snapshots=cast("list[dict[str, object]]", input_snapshots),
        policy_assessment=policy_assessment,
    )
    updated["historical_live_run_upgrade_state"] = (
        _resolve_historical_live_run_upgrade_state(
            manifest=effective_manifest,
            input_snapshots=cast("list[dict[str, object]]", input_snapshots),
            policy_assessment=policy_assessment,
        )
    )
    updated["broader_historical_exact_replay_state"] = (
        _resolve_broader_historical_exact_replay_state(
            manifest=effective_manifest,
            input_snapshots=cast("list[dict[str, object]]", input_snapshots),
            policy_assessment=policy_assessment,
        )
    )
    updated["source_posture"] = _resolve_source_posture(policy_assessment)
    return updated, exact_replay_eligible, replay_mode, continuation_mode


def _refresh_replay_summary_update_snapshot_fields(
    updated: dict[str, object],
    input_snapshots: list[object],
    exact_replay_eligible: bool,
    replay_mode: str,
    policy_assessment: object,
) -> dict[str, object]:
    """Update snapshot-related fields in summary."""
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
    (
        effective_manifest,
        policy_assessment,
        resume_requested,
    ) = _refresh_replay_summary_build_policy_assessment(
        manifest=manifest,
        summary=summary,
        input_snapshots=cast("list[object]", input_snapshots),
    )
    requested_exact_replay = bool(summary.get("requested_exact_replay", False))
    updated = dict(summary)
    (
        updated,
        exact_replay_eligible,
        replay_mode,
        continuation_mode,
    ) = _refresh_replay_summary_update_replay_fields(
        updated=updated,
        effective_manifest=effective_manifest,
        policy_assessment=policy_assessment,
        input_snapshots=cast("list[object]", input_snapshots),
        resume_requested=resume_requested,
        requested_exact_replay=requested_exact_replay,
    )
    updated = _refresh_replay_summary_update_snapshot_fields(
        updated=updated,
        input_snapshots=cast("list[object]", input_snapshots),
        exact_replay_eligible=exact_replay_eligible,
        replay_mode=replay_mode,
        policy_assessment=policy_assessment,
    )
    updated["resume_contract"] = _build_resume_contract(
        manifest=effective_manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        policy_assessment=policy_assessment,
    )
    return updated


def _build_effective_source_refs(
    *,
    manifest: RunManifest,
    input_snapshots: list[object],
) -> tuple[RunSourceRef, ...]:
    snapshots_by_source = _group_input_snapshots_by_source(
        manifest=manifest,
        input_snapshots=input_snapshots,
    )
    if not snapshots_by_source:
        return manifest.source_refs
    effective_refs = _merge_manifest_source_refs(
        manifest=manifest,
        snapshots_by_source=snapshots_by_source,
    )
    effective_refs.extend(_build_additional_source_refs(snapshots_by_source))
    return tuple(effective_refs)


def _group_input_snapshots_by_source(
    *,
    manifest: RunManifest,
    input_snapshots: list[object],
) -> dict[tuple[str, str, str, str | None], list[RunInputSnapshotRef]]:
    """Group input snapshots by their effective source identity."""
    snapshots_by_source: dict[
        tuple[str, str, str, str | None],
        list[RunInputSnapshotRef],
    ] = {}
    for item in input_snapshots:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or manifest.provider).strip()
        entity = str(item.get("entity") or manifest.entity).strip()
        pipeline_name = str(item.get("pipeline_name") or manifest.pipeline_name).strip()
        query_value = item.get("query")
        query = str(query_value).strip() if query_value is not None else None
        snapshots_by_source.setdefault(
            (provider, entity, pipeline_name, query),
            [],
        ).append(_build_snapshot_ref(item))
    return snapshots_by_source


def _merge_manifest_source_refs(
    *,
    manifest: RunManifest,
    snapshots_by_source: dict[
        tuple[str, str, str, str | None], list[RunInputSnapshotRef]
    ],
) -> list[RunSourceRef]:
    """Attach grouped snapshot refs to manifest-declared source refs."""
    effective_refs: list[RunSourceRef] = []
    for source_ref in manifest.source_refs:
        snapshots = _pop_matching_source_snapshots(
            snapshots_by_source=snapshots_by_source,
            provider=source_ref.provider,
            entity=source_ref.entity,
            pipeline_name=source_ref.pipeline_name,
            query=source_ref.query,
        )
        effective_refs.append(
            RunSourceRef(
                provider=source_ref.provider,
                entity=source_ref.entity,
                pipeline_name=source_ref.pipeline_name,
                query=source_ref.query,
                input_snapshots=tuple(snapshots),
            )
        )
    return effective_refs


def _pop_matching_source_snapshots(
    *,
    snapshots_by_source: dict[
        tuple[str, str, str, str | None], list[RunInputSnapshotRef]
    ],
    provider: str,
    entity: str,
    pipeline_name: str,
    query: str | None,
) -> list[RunInputSnapshotRef]:
    """Resolve ledger-derived snapshots back onto a manifest-declared source.

    Manifest source refs often omit `query` while post-manifest ledger evidence
    can carry a concrete query string. In that case, all snapshots for the same
    provider/entity/pipeline triple belong to the declared source and should not
    create an extra synthetic source ref that would incorrectly mark the
    envelope as partial.
    """
    exact_key = (provider, entity, pipeline_name, query)
    if query is not None:
        return snapshots_by_source.pop(exact_key, [])

    matched_keys = [
        key
        for key in snapshots_by_source
        if key[:3] == (provider, entity, pipeline_name)
    ]
    snapshots: list[RunInputSnapshotRef] = []
    for key in matched_keys:
        snapshots.extend(snapshots_by_source.pop(key, []))
    return snapshots


def _build_additional_source_refs(
    snapshots_by_source: dict[
        tuple[str, str, str, str | None], list[RunInputSnapshotRef]
    ],
) -> list[RunSourceRef]:
    """Build source refs discovered only from input snapshots."""
    return [
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=pipeline_name,
            query=query,
            input_snapshots=tuple(snapshots),
        )
        for (provider, entity, pipeline_name, query), snapshots in sorted(
            snapshots_by_source.items()
        )
    ]


def _build_snapshot_ref(snapshot: dict[str, object]) -> RunInputSnapshotRef:
    captured_at_value = snapshot.get("captured_at")
    captured_at = None
    if isinstance(captured_at_value, str) and captured_at_value.strip():
        captured_at = datetime.fromisoformat(captured_at_value)
    return RunInputSnapshotRef(
        snapshot_id=str(snapshot.get("snapshot_id") or ""),
        content_hash=str(snapshot.get("content_hash") or ""),
        immutable_uri=cast("str | None", snapshot.get("immutable_uri")),
        query_fingerprint=cast("str | None", snapshot.get("query_fingerprint")),
        storage_provider=cast("str | None", snapshot.get("storage_provider")),
        object_bucket=cast("str | None", snapshot.get("object_bucket")),
        object_key=cast("str | None", snapshot.get("object_key")),
        object_version_id=cast("str | None", snapshot.get("object_version_id")),
        etag=cast("str | None", snapshot.get("etag")),
        last_modified=cast("str | None", snapshot.get("last_modified")),
        captured_at=captured_at,
    )


__all__ = ["build_diagnostics_summary"]

_RICH_COMPOSITE_REPLAY_EVENTS = frozenset(
    {
        COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
        COMPOSITE_ENRICHER_COMPLETED_EVENT,
        COMPOSITE_MERGE_COMPLETED_EVENT,
    }
)


def _attach_rich_composite_replay_support(
    summary: dict[str, object],
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Mark composite rich replay support only when ledger evidence is present."""
    observed_events = {
        entry.event_type
        for entry in ledger_entries
        if entry.event_type in _RICH_COMPOSITE_REPLAY_EVENTS
    }
    if not _RICH_COMPOSITE_REPLAY_EVENTS.issubset(observed_events):
        return summary
    updated = dict(summary)
    updated["composite_resume_rich_replay_supported"] = True
    return updated
