"""Private finalization helpers for run-manifest diagnostics assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_support import (
    merge_ledger_input_snapshots_into_summary,
)
from bioetl.application.services.control_plane.manifest.diagnostics.source_refs import (
    _attach_rich_composite_replay_support,
)
from bioetl.application.services.control_plane.run_manifest_diagnostics_support import (
    _build_final_summary,
    _build_runtime_views,
    _build_unified_reproducibility_diagnostics,
    _FinalSummaryRequest,
    _process_ledger_entries,
    _RuntimeViewsRequest,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
)

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunLedgerEntry, RunManifest


@dataclass(frozen=True, slots=True)
class _LedgerEnrichedSummary:
    """Base summary after ledger-derived enrichment has been applied."""

    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class _ProcessedLedgerDiagnostics:
    """Structured ledger diagnostics inputs for final summary assembly."""

    family_counter: object
    type_counter: object
    artifact_refs: object
    lineage_fragment_ids: object
    dq_rule_ids: object
    dq_dispositions: object
    dq_report_paths: object
    dq_violation_kinds: object
    cross_validation_rule_ids: object
    cross_validation_config_paths: object
    cross_validation_quarantine_policies: object
    cross_validation_replay_contracts: object
    occurrence_only_diagnostic_scopes: object
    dq_signal_present: bool
    cross_validation_signal_present: bool
    missing_link_count: int
    correlation_anchor_gaps: object
    resume_diagnostics: object


def attach_summary_reproducibility_views(summary: dict[str, object]) -> None:
    """Attach canonical reproducibility diagnostics and score overlays."""
    summary["reproducibility_diagnostics"] = _build_unified_reproducibility_diagnostics(
        summary
    )
    summary["reproducibility_audit_score"] = build_reproducibility_audit_scoring(
        summary
    )


def attach_base_summary_runtime_views(
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
    attach_summary_reproducibility_views(summary)


def _build_ledger_enriched_summary(
    *,
    manifest: RunManifest,
    summary: dict[str, object],
    ledger_entries: tuple[RunLedgerEntry, ...],
    refresh_replay_summary_fn: Callable[..., dict[str, object]],
) -> _LedgerEnrichedSummary:
    """Apply post-ledger enrichment before final summary synthesis."""
    enriched = merge_ledger_input_snapshots_into_summary(
        summary,
        ledger_entries,
    )
    enriched = _attach_rich_composite_replay_support(
        enriched,
        ledger_entries,
    )
    enriched = refresh_replay_summary_fn(
        manifest=manifest,
        summary=enriched,
    )
    return _LedgerEnrichedSummary(payload=enriched)


def _process_ledger_diagnostics(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> _ProcessedLedgerDiagnostics:
    """Return typed ledger diagnostics inputs for final-summary assembly."""
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
    return _ProcessedLedgerDiagnostics(
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
        cross_validation_quarantine_policies=cross_validation_quarantine_policies,
        cross_validation_replay_contracts=cross_validation_replay_contracts,
        occurrence_only_diagnostic_scopes=occurrence_only_diagnostic_scopes,
        dq_signal_present=dq_signal_present,
        cross_validation_signal_present=cross_validation_signal_present,
        missing_link_count=missing_link_count,
        correlation_anchor_gaps=correlation_anchor_gaps,
        resume_diagnostics=resume_diagnostics,
    )


def build_final_diagnostics_summary(
    *,
    manifest: RunManifest,
    base_summary: dict[str, object],
    ledger_entries: tuple[RunLedgerEntry, ...],
    refresh_replay_summary_fn: Callable[..., dict[str, object]],
) -> dict[str, object]:
    """Build final diagnostics summary from base summary and ledger evidence."""
    enriched_summary = _build_ledger_enriched_summary(
        manifest=manifest,
        summary=base_summary,
        ledger_entries=ledger_entries,
        refresh_replay_summary_fn=refresh_replay_summary_fn,
    ).payload
    processed_ledger = _process_ledger_diagnostics(ledger_entries)
    final_summary = _build_final_summary(
        _FinalSummaryRequest(
            manifest=manifest,
            base_summary=enriched_summary,
            ledger_entries=ledger_entries,
            family_counter=processed_ledger.family_counter,
            type_counter=processed_ledger.type_counter,
            artifact_refs=processed_ledger.artifact_refs,
            lineage_fragment_ids=processed_ledger.lineage_fragment_ids,
            dq_rule_ids=processed_ledger.dq_rule_ids,
            dq_dispositions=processed_ledger.dq_dispositions,
            dq_report_paths=processed_ledger.dq_report_paths,
            dq_violation_kinds=processed_ledger.dq_violation_kinds,
            cross_validation_rule_ids=processed_ledger.cross_validation_rule_ids,
            cross_validation_config_paths=(
                processed_ledger.cross_validation_config_paths
            ),
            cross_validation_quarantine_policies=(
                processed_ledger.cross_validation_quarantine_policies
            ),
            cross_validation_replay_contracts=(
                processed_ledger.cross_validation_replay_contracts
            ),
            occurrence_only_diagnostic_scopes=(
                processed_ledger.occurrence_only_diagnostic_scopes
            ),
            dq_signal_present=processed_ledger.dq_signal_present,
            cross_validation_signal_present=(
                processed_ledger.cross_validation_signal_present
            ),
            missing_link_count=processed_ledger.missing_link_count,
            correlation_anchor_gaps=processed_ledger.correlation_anchor_gaps,
            resume_diagnostics=processed_ledger.resume_diagnostics,
        )
    )
    attach_summary_reproducibility_views(final_summary)
    return final_summary
