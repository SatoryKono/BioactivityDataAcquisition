"""Private finalization helpers for run-manifest diagnostics assembly."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.diagnostics.ledger_processing import (
    build_ledger_dq_details_summary,
)
from bioetl.application.services.control_plane.manifest.diagnostics.main_helpers import (
    _build_unified_reproducibility_diagnostics,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_summary import (
    merge_ledger_input_snapshots_into_summary,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary import (
    _build_final_summary,
    _build_runtime_views,
    _FinalSummaryRequest,
    _RuntimeViewsRequest,
    attach_base_summary_artifact_defaults,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.dq_details import (
        DQDetailsSummary,
    )
    from bioetl.domain.control_plane import RunLedgerEntry, RunManifest


@dataclass(frozen=True, slots=True)
class _LedgerEnrichedSummary:
    """Base summary after ledger-derived enrichment has been applied."""

    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class _ProcessedLedgerDiagnostics:
    """Structured ledger diagnostics inputs for final summary assembly."""

    dq_details: DQDetailsSummary
    artifact_refs: list[dict[str, object]]
    type_counter: Counter[str]
    lineage_fragment_ids: set[str]
    family_counter: Counter[str]
    missing_link_count: int
    correlation_anchor_gaps: dict[str, int]
    resume_diagnostics: dict[str, object] | None


def attach_summary_reproducibility_views(summary: dict[str, object]) -> None:
    """Attach canonical reproducibility diagnostics and score overlays."""
    summary["reproducibility_diagnostics"] = _build_unified_reproducibility_diagnostics(
        summary
    )
    summary["reproducibility_audit_score"] = build_reproducibility_audit_scoring(
        summary
    )


def refresh_reproducibility_audit_score(summary: dict[str, object]) -> None:
    """Refresh the score after inspection adds governed replay evidence."""
    summary["reproducibility_audit_score"] = build_reproducibility_audit_scoring(
        summary
    )


def attach_base_summary_runtime_views(
    manifest: RunManifest,
    summary: dict[str, object],
) -> None:
    """Attach persistence, alert, and scoring overlays to base summary."""
    attach_base_summary_artifact_defaults(manifest=manifest, summary=summary)
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
    processed, dq_details = build_ledger_dq_details_summary(ledger_entries)
    (
        family_counter,
        type_counter,
        artifact_refs,
        lineage_fragment_ids,
        _dq_rule_ids,
        _dq_dispositions,
        _dq_report_paths,
        _dq_violation_kinds,
        _cross_validation_rule_ids,
        _cross_validation_config_paths,
        _cross_validation_quarantine_policies,
        _cross_validation_replay_contracts,
        _occurrence_only_diagnostic_scopes,
        _dq_signal_present,
        _cross_validation_signal_present,
        missing_link_count,
        correlation_anchor_gaps,
        resume_diagnostics,
    ) = processed
    return _ProcessedLedgerDiagnostics(
        family_counter=family_counter,
        type_counter=type_counter,
        artifact_refs=artifact_refs,
        lineage_fragment_ids=lineage_fragment_ids,
        dq_details=dq_details,
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
            dq_details=processed_ledger.dq_details,
            missing_link_count=processed_ledger.missing_link_count,
            correlation_anchor_gaps=processed_ledger.correlation_anchor_gaps,
            resume_diagnostics=processed_ledger.resume_diagnostics,
        )
    )
    attach_summary_reproducibility_views(final_summary)
    return final_summary
