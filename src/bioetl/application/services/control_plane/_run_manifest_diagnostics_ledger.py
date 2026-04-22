"""Ledger aggregation helpers for manifest diagnostics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from bioetl.application.services.control_plane._run_manifest_diagnostics_helpers import (
    extract_dq_details,
    update_correlation_anchor_gaps,
)
from bioetl.domain.control_plane import RunLedgerEntry


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
        for field in (
            "compatibility_disposition",
            "resume_rejected",
            "execution_identity_compatible",
        ):
            value = details.get(field)
            if value is not None:
                diagnostics[field] = value
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
    family_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    artifact_refs: list[dict[str, object]] = []
    lineage_fragment_ids: set[str] = set()
    dq_rule_ids: set[str] = set()
    dq_dispositions: set[str] = set()
    dq_report_paths: set[str] = set()
    dq_violation_kinds: set[str] = set()
    cross_validation_rule_ids: set[str] = set()
    cross_validation_config_paths: set[str] = set()
    cross_validation_quarantine_policies: set[str] = set()
    cross_validation_replay_contracts: set[str] = set()
    occurrence_only_diagnostic_scopes: set[str] = set()
    dq_signal_present = False
    cross_validation_signal_present = False
    missing_link_count = 0
    correlation_anchor_gaps = {
        "resolved_config_hash": 0,
        "effective_config_hash": 0,
        "contract_ref": 0,
        "contract_version": 0,
        "composite_run_id": 0,
    }
    resume_diagnostics = _extract_resume_diagnostics(ledger_entries)

    for entry in ledger_entries:
        family_counter.update([entry.event_family or "diagnostic"])
        type_counter.update([entry.event_type])
        artifact_ref = _build_artifact_ref(entry)
        if artifact_ref is not None:
            artifact_refs.append(artifact_ref)
            if (
                artifact_ref.get("dataset_ref") is None
                and artifact_ref.get("lineage_fragment_id") is None
            ):
                missing_link_count += 1
        if entry.lineage_fragment_id:
            lineage_fragment_ids.add(entry.lineage_fragment_id)
        dq_details = extract_dq_details(entry)
        dq_rule_ids.update(dq_details["rule_ids"])
        dq_dispositions.update(dq_details["dispositions"])
        dq_report_paths.update(dq_details["report_paths"])
        dq_violation_kinds.update(dq_details["violation_kinds"])
        cross_validation_rule_ids.update(dq_details["cross_validation_rule_ids"])
        cross_validation_config_paths.update(
            dq_details["cross_validation_config_paths"]
        )
        cross_validation_quarantine_policies.update(
            dq_details["cross_validation_quarantine_policies"]
        )
        cross_validation_replay_contracts.update(
            dq_details["cross_validation_replay_contracts"]
        )
        occurrence_only_diagnostic_scopes.update(
            dq_details["occurrence_only_diagnostic_scopes"]
        )
        dq_signal_present = dq_signal_present or dq_details["has_signal"]
        cross_validation_signal_present = (
            cross_validation_signal_present or dq_details["has_cross_validation_signal"]
        )
        update_correlation_anchor_gaps(correlation_anchor_gaps, entry)

    return (
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
        "record_count",
        "total_bytes",
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
