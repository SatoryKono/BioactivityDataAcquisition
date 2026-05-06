"""Ledger aggregation helpers for manifest diagnostics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field

from bioetl.application.services.control_plane._run_manifest_diagnostics_helpers import (
    extract_dq_details,
    update_correlation_anchor_gaps,
)
from bioetl.domain.control_plane import RunLedgerEntry


@dataclass(slots=True)
class _LedgerProcessingState:
    """Mutable aggregation state for manifest ledger diagnostics."""

    family_counter: Counter[str] = field(default_factory=Counter)
    type_counter: Counter[str] = field(default_factory=Counter)
    artifact_refs: list[dict[str, object]] = field(default_factory=list)
    lineage_fragment_ids: set[str] = field(default_factory=set)
    dq_rule_ids: set[str] = field(default_factory=set)
    dq_dispositions: set[str] = field(default_factory=set)
    dq_report_paths: set[str] = field(default_factory=set)
    dq_violation_kinds: set[str] = field(default_factory=set)
    cross_validation_rule_ids: set[str] = field(default_factory=set)
    cross_validation_config_paths: set[str] = field(default_factory=set)
    cross_validation_quarantine_policies: set[str] = field(default_factory=set)
    cross_validation_replay_contracts: set[str] = field(default_factory=set)
    occurrence_only_diagnostic_scopes: set[str] = field(default_factory=set)
    dq_signal_present: bool = False
    cross_validation_signal_present: bool = False
    missing_link_count: int = 0
    correlation_anchor_gaps: dict[str, int] = field(
        default_factory=lambda: {
            "resolved_config_hash": 0,
            "effective_config_hash": 0,
            "contract_ref": 0,
            "contract_version": 0,
            "composite_run_id": 0,
        }
    )


def _resume_diagnostics_present(details: Mapping[str, object]) -> bool:
    """Return whether one ledger detail payload carries resume diagnostics."""
    return any(
        details.get(field) is not None
        for field in (
            "compatibility_disposition",
            "resume_rejected",
            "execution_identity_compatible",
            "messages",
            "current_identity",
            "checkpoint_identity",
        )
    )


def _copy_resume_mapping(
    diagnostics: dict[str, object],
    details: Mapping[str, object],
    field: str,
) -> None:
    """Copy one mapping field into resume diagnostics when present."""
    value = details.get(field)
    if isinstance(value, Mapping):
        diagnostics[field] = dict(value)


def _extract_resume_diagnostics(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object] | None:
    """Return the latest persisted resume diagnostics, if any."""
    for entry in reversed(ledger_entries):
        details = entry.details
        if not isinstance(details, Mapping):
            continue
        if not _resume_diagnostics_present(details):
            continue
        diagnostics: dict[str, object] = {
            "source_event_type": entry.event_type,
            "source_status": entry.status,
        }
        for field_name in (
            "compatibility_disposition",
            "resume_rejected",
            "execution_identity_compatible",
        ):
            value = details.get(field_name)
            if value is not None:
                diagnostics[field_name] = value
        messages = details.get("messages")
        if isinstance(messages, list):
            diagnostics["messages"] = list(messages)
        _copy_resume_mapping(diagnostics, details, "current_identity")
        _copy_resume_mapping(diagnostics, details, "checkpoint_identity")
        return diagnostics
    return None


def _process_ledger_entries(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> tuple[
    Counter[str],
    Counter[str],
    list[dict[str, object]],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    bool,
    bool,
    int,
    dict[str, int],
    dict[str, object] | None,
]:
    """Process ledger entries and extract statistics."""
    state = _LedgerProcessingState()
    resume_diagnostics = _extract_resume_diagnostics(ledger_entries)

    for entry in ledger_entries:
        _update_ledger_processing_state(state, entry)

    return _freeze_ledger_processing_state(state, resume_diagnostics)


def _update_ledger_processing_state(
    state: _LedgerProcessingState,
    entry: RunLedgerEntry,
) -> None:
    """Accumulate one ledger entry into the diagnostics state."""
    state.family_counter.update([entry.event_family or "diagnostic"])
    state.type_counter.update([entry.event_type])
    _register_artifact_ref(state, entry)
    if entry.lineage_fragment_id:
        state.lineage_fragment_ids.add(entry.lineage_fragment_id)
    _update_dq_statistics(state, entry)
    update_correlation_anchor_gaps(state.correlation_anchor_gaps, entry)


def _register_artifact_ref(
    state: _LedgerProcessingState,
    entry: RunLedgerEntry,
) -> None:
    """Record artifact references and missing-link counters for one entry."""
    artifact_ref = _build_artifact_ref(entry)
    if artifact_ref is None:
        return
    state.artifact_refs.append(artifact_ref)
    if (
        artifact_ref.get("dataset_ref") is None
        and artifact_ref.get("lineage_fragment_id") is None
    ):
        state.missing_link_count += 1


def _update_dq_statistics(
    state: _LedgerProcessingState,
    entry: RunLedgerEntry,
) -> None:
    """Merge extracted DQ details from one ledger entry into aggregate state."""
    dq_details = extract_dq_details(entry)
    state.dq_rule_ids.update(dq_details["rule_ids"])
    state.dq_dispositions.update(dq_details["dispositions"])
    state.dq_report_paths.update(dq_details["report_paths"])
    state.dq_violation_kinds.update(dq_details["violation_kinds"])
    state.cross_validation_rule_ids.update(dq_details["cross_validation_rule_ids"])
    state.cross_validation_config_paths.update(
        dq_details["cross_validation_config_paths"]
    )
    state.cross_validation_quarantine_policies.update(
        dq_details["cross_validation_quarantine_policies"]
    )
    state.cross_validation_replay_contracts.update(
        dq_details["cross_validation_replay_contracts"]
    )
    state.occurrence_only_diagnostic_scopes.update(
        dq_details["occurrence_only_diagnostic_scopes"]
    )
    state.dq_signal_present = state.dq_signal_present or dq_details["has_signal"]
    state.cross_validation_signal_present = (
        state.cross_validation_signal_present
        or dq_details["has_cross_validation_signal"]
    )


def _freeze_ledger_processing_state(
    state: _LedgerProcessingState,
    resume_diagnostics: dict[str, object] | None,
) -> tuple[
    Counter[str],
    Counter[str],
    list[dict[str, object]],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    bool,
    bool,
    int,
    dict[str, int],
    dict[str, object] | None,
]:
    """Return the legacy tuple payload expected by diagnostics callers."""
    return (
        state.family_counter,
        state.type_counter,
        state.artifact_refs,
        state.lineage_fragment_ids,
        state.dq_rule_ids,
        state.dq_dispositions,
        state.dq_report_paths,
        state.dq_violation_kinds,
        state.cross_validation_rule_ids,
        state.cross_validation_config_paths,
        state.cross_validation_quarantine_policies,
        state.cross_validation_replay_contracts,
        state.occurrence_only_diagnostic_scopes,
        state.dq_signal_present,
        state.cross_validation_signal_present,
        state.missing_link_count,
        state.correlation_anchor_gaps,
        resume_diagnostics,
    )


def _build_artifact_ref(entry: RunLedgerEntry) -> dict[str, object] | None:
    """Return one artifact reference emitted from a ledger entry."""
    if entry.event_family != "artifact" and entry.event_type != "artifact_published":
        return None
    details = entry.details or {}
    artifact_path = details.get("artifact_path")
    artifact_ref: dict[str, object] = {
        "event_type": entry.event_type,
        "stage": entry.stage,
        "artifact_id": entry.dataset_ref,
        "dataset_ref": entry.dataset_ref,
        "lineage_fragment_id": entry.lineage_fragment_id,
        "artifact_path": None if artifact_path is None else str(artifact_path),
    }
    for detail_key in (
        "metadata_path",
        "artifact_kind",
        "artifact_semantics",
        "record_count",
        "total_bytes",
        "content_hash",
        "hash_algorithm",
        "execution_fingerprint",
        "input_snapshot_count",
        "input_snapshot_ids",
        "input_snapshot_content_hashes",
        "pipeline_name",
        "provider",
        "entity",
        "run_id",
        "manifest_id",
    ):
        detail_value = details.get(detail_key)
        if detail_value is not None:
            artifact_ref[detail_key] = detail_value
    return artifact_ref


def _resolve_policy_value(values: set[str]) -> str | None:
    """Return one canonical policy value or an explicit mixed-policy marker."""
    if not values:
        return None
    if len(values) == 1:
        return next(iter(values))
    return "mixed"
