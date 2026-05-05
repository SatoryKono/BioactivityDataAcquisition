"""Diagnostics helpers for run manifest inspection service."""

from __future__ import annotations

from typing import cast

from bioetl.application.services.control_plane._run_manifest_diagnostics_base import (
    _build_base_summary_payload,
    _build_current_checkpoint_anchor_payload,
    _build_effective_config_diagnostics,
    _build_resume_anchor_comparison,
    _resolve_base_summary_replay_context,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_ledger import (
    _process_ledger_entries,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_persistence import (
    build_alert_signals,
    build_next_steps,
    build_persistence_profile,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay import (
    _is_composite_execution_context,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_summary import (
    _build_final_summary,
    _FinalSummaryRequest,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest


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


def _build_unified_reproducibility_diagnostics(
    summary: dict[str, object],
) -> dict[str, object]:
    """Return a single operator-facing reproducibility diagnostics surface."""
    persistence_profile = cast(
        "dict[str, object]", summary.get("persistence_profile", {})
    )
    produced_artifact_trace = cast(
        "dict[str, object]",
        summary.get("produced_artifact_trace", {}),
    )
    return {
        "policy": {
            "required_persistence_profile": summary.get("required_persistence_profile"),
            "attained_profile": persistence_profile.get("attained_profile"),
            "required_profile_satisfied": persistence_profile.get(
                "required_profile_satisfied"
            ),
            "required_profile_missing_requirements": persistence_profile.get(
                "required_profile_missing_requirements",
                [],
            ),
            "replay_capability": summary.get("replay_capability"),
            "operator_replay_mode": summary.get("operator_replay_mode"),
            "replay_mode": summary.get("replay_mode"),
            "continuation_mode": summary.get("continuation_mode"),
            "replay_family_contract": summary.get("replay_family_contract"),
            "exact_replay_support_boundary": summary.get(
                "exact_replay_support_boundary"
            ),
            "exact_replay_blockers": summary.get("exact_replay_blockers", []),
            "policy_assessment": summary.get(
                "reproducibility_policy_assessment",
                {},
            ),
        },
        "semantic_identity": {
            "execution_fingerprint": summary.get("execution_fingerprint"),
            "config_hash_compatibility_anchor": summary.get("config_hash"),
            "resolved_config_hash": summary.get("resolved_config_hash"),
            "effective_config_hash": summary.get("effective_config_hash"),
            "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
            "input_snapshot_identity_fingerprint": summary.get(
                "input_snapshot_identity_fingerprint"
            ),
            "snapshot_status": summary.get("snapshot_status"),
            "input_snapshot_ids": summary.get("input_snapshot_ids", []),
        },
        "effective_config": _build_effective_config_diagnostics(summary),
        "occurrence_identity": {
            "run_id": summary.get("run_id"),
            "manifest_id": summary.get("manifest_id"),
            "manifest_created_at": summary.get("manifest_created_at"),
            "occurrence_only_diagnostics": summary.get(
                "occurrence_only_diagnostics",
                [],
            ),
        },
        "checkpoint_anchors": {
            "resume_contract": summary.get("resume_contract"),
            "resume_diagnostics": summary.get("resume_diagnostics"),
            "current_manifest_anchors": _build_current_checkpoint_anchor_payload(
                summary
            ),
            "resume_anchor_comparison": _build_resume_anchor_comparison(summary),
        },
        "lineage": {
            "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
            "lineage_fragment_ids": summary.get("lineage_fragment_ids", []),
            "planned_artifact_count": summary.get("planned_artifact_count"),
            "published_artifact_count": summary.get("published_artifact_count"),
            "produced_artifact_trace_complete": produced_artifact_trace.get("complete"),
        },
    }


def build_diagnostics_summary(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Build compact operator-oriented diagnostics summary."""
    base_summary = _build_base_summary(manifest)

    if not ledger_entries:
        return base_summary

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


__all__ = ["build_diagnostics_summary"]
