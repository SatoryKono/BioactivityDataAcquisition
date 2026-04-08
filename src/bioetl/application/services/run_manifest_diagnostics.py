"""Diagnostics helpers for run manifest inspection service."""

from __future__ import annotations

from collections import Counter
from typing import TypedDict

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest


class DQDetailsSummary(TypedDict):
    """Normalized DQ anchor sets extracted from one ledger entry."""

    rule_ids: set[str]
    dispositions: set[str]
    report_paths: set[str]
    violation_kinds: set[str]
    cross_validation_rule_ids: set[str]
    cross_validation_config_paths: set[str]
    has_signal: bool
    has_cross_validation_signal: bool


def _build_base_summary(
    manifest: RunManifest,
) -> dict[str, object]:
    """Build base summary from manifest code provenance."""
    code_provenance = manifest.code_provenance
    return {
        "execution_fingerprint": manifest.execution_fingerprint,
        "config_hash": code_provenance.config_hash,
        "effective_config_hash": code_provenance.config_hash,
        "contract_ref": code_provenance.contract_ref,
        "contract_version": code_provenance.contract_version,
        "dq_policy_ref": code_provenance.dq_policy_ref,
        "rule_bundle_version": code_provenance.rule_bundle_version,
        "dq_contract_compatibility_hash": (
            code_provenance.dq_contract_compatibility_hash
        ),
        "effective_config_artifact_id": code_provenance.effective_config_artifact_id,
    }


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
    bool,
    bool,
    int,
    dict[str, int],
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
    dq_signal_present = False
    cross_validation_signal_present = False
    missing_link_count = 0
    correlation_anchor_gaps = {
        "effective_config_hash": 0,
        "contract_ref": 0,
        "data_contract_version": 0,
        "composite_run_id": 0,
    }
    
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
        dq_details = _extract_dq_details(entry)
        dq_rule_ids.update(dq_details["rule_ids"])
        dq_dispositions.update(dq_details["dispositions"])
        dq_report_paths.update(dq_details["report_paths"])
        dq_violation_kinds.update(dq_details["violation_kinds"])
        cross_validation_rule_ids.update(dq_details["cross_validation_rule_ids"])
        cross_validation_config_paths.update(
            dq_details["cross_validation_config_paths"]
        )
        dq_signal_present = dq_signal_present or dq_details["has_signal"]
        cross_validation_signal_present = (
            cross_validation_signal_present or dq_details["has_cross_validation_signal"]
        )
        _update_correlation_anchor_gaps(
            correlation_anchor_gaps,
            entry,
        )
    
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
        dq_signal_present,
        cross_validation_signal_present,
        missing_link_count,
        correlation_anchor_gaps,
    )


def _build_final_summary(
    base_summary: dict[str, object],
    ledger_entries: tuple[RunLedgerEntry, ...],
    family_counter: Counter[str],
    type_counter: Counter[str],
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    dq_rule_ids: set[str],
    dq_dispositions: set[str],
    dq_report_paths: set[str],
    dq_violation_kinds: set[str],
    cross_validation_rule_ids: set[str],
    cross_validation_config_paths: set[str],
    dq_signal_present: bool,
    cross_validation_signal_present: bool,
    missing_link_count: int,
    correlation_anchor_gaps: dict[str, int],
) -> dict[str, object]:
    """Build final summary with all processed data."""
    latest_entry = ledger_entries[-1]
    alert_signals = _build_alert_signals(
        latest_status=latest_entry.status,
        artifact_refs=artifact_refs,
        lineage_fragment_ids=lineage_fragment_ids,
        missing_link_count=missing_link_count,
        dq_signal_present=dq_signal_present,
        cross_validation_signal_present=cross_validation_signal_present,
    )
    next_steps = _build_next_steps(alert_signals)
    
    summary = base_summary.copy()
    summary.update(
        {
            "total_events": len(ledger_entries),
            "latest_event_type": latest_entry.event_type,
            "latest_status": latest_entry.status,
            "event_family_counts": dict(sorted(family_counter.items())),
            "event_type_counts": dict(sorted(type_counter.items())),
            "artifact_refs": artifact_refs,
            "lineage_fragment_ids": sorted(lineage_fragment_ids),
            "missing_artifact_links": missing_link_count,
            "dq_rule_ids": sorted(dq_rule_ids),
            "dq_dispositions": sorted(dq_dispositions),
            "dq_report_paths": sorted(dq_report_paths),
            "dq_violation_kinds": sorted(dq_violation_kinds),
            "cross_validation_rule_ids": sorted(cross_validation_rule_ids),
            "cross_validation_config_paths": sorted(cross_validation_config_paths),
            "cross_validation_signal_present": cross_validation_signal_present,
            "correlation_anchor_gaps": correlation_anchor_gaps,
            "alert_signals": alert_signals,
            "next_steps": next_steps,
        }
    )
    return summary


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
        dq_signal_present,
        cross_validation_signal_present,
        missing_link_count,
        correlation_anchor_gaps,
    ) = _process_ledger_entries(ledger_entries)
    
    return _build_final_summary(
        base_summary,
        ledger_entries,
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
        dq_signal_present,
        cross_validation_signal_present,
        missing_link_count,
        correlation_anchor_gaps,
    )


def _build_artifact_ref(entry: RunLedgerEntry) -> dict[str, object] | None:
    if entry.event_family != "artifact" and entry.event_type != "artifact_published":
        return None
    details = entry.details or {}
    artifact_path = details.get("artifact_path")
    return {
        "event_type": entry.event_type,
        "stage": entry.stage,
        "dataset_ref": entry.dataset_ref,
        "lineage_fragment_id": entry.lineage_fragment_id,
        "artifact_path": None if artifact_path is None else str(artifact_path),
    }


def _build_alert_signals(
    *,
    latest_status: str | None,
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    missing_link_count: int,
    dq_signal_present: bool,
    cross_validation_signal_present: bool,
) -> dict[str, bool]:
    """Map diagnostics summary to alert-oriented boolean signals."""
    latest_status_normalized = (latest_status or "").strip().lower()
    artifact_ref_count = len(artifact_refs)
    has_artifact_refs = artifact_ref_count > 0
    return {
        "run_failed": latest_status_normalized == "failed",
        "run_shutdown": latest_status_normalized == "shutdown",
        "artifact_linkage_gap": missing_link_count > 0,
        "lineage_gap": has_artifact_refs and not lineage_fragment_ids,
        "dq_signal_present": dq_signal_present,
        "cross_validation_signal_present": cross_validation_signal_present,
    }


def _build_next_steps(alert_signals: dict[str, bool]) -> list[str]:
    """Return operator-oriented next steps based on active alert signals."""
    steps: list[str] = []
    if alert_signals.get("run_failed", False):
        steps.append(
            "Inspect failure classification and decide retry/quarantine/escalation."
        )
    if alert_signals.get("artifact_linkage_gap", False):
        steps.append(
            "Validate artifact publication metadata and repair dataset/lineage links."
        )
    if alert_signals.get("lineage_gap", False):
        steps.append(
            "Investigate lineage persistence for published artifacts before restart."
        )
    if alert_signals.get("dq_signal_present", False):
        steps.append(
            "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation."
        )
    if alert_signals.get("cross_validation_signal_present", False):
        steps.append(
            "Review cross-validation mismatch outcomes and composite policy anchors before retry or quarantine changes."
        )
    if alert_signals.get("run_shutdown", False):
        steps.append(
            "Confirm graceful shutdown reason and resume policy compatibility."
        )
    if not steps:
        steps.append("No alert signals detected; continue routine monitoring.")
    return steps


def _collect_dq_values(
    details: dict[str, object],
    *,
    single_key: str | None = None,
    collection_keys: tuple[str, ...] = (),
) -> set[str]:
    """Collect one optional scalar key and list-like keys into a string set."""
    values: set[str] = set()
    if single_key is not None:
        single_value = details.get(single_key)
        if single_value is not None:
            values.add(str(single_value))
    for key in collection_keys:
        values.update(_load_str_collection(details.get(key)))
    return values


def _extract_cross_validation_sets(
    rule_ids: set[str],
    config_paths: set[str],
) -> tuple[set[str], set[str]]:
    """Extract cross-validation specific subsets from DQ anchors."""
    cross_validation_rule_ids = {
        rule_id
        for rule_id in rule_ids
        if rule_id.startswith("composite.cross_validation.")
    }
    cross_validation_config_paths = {
        config_path for config_path in config_paths if config_path == "cross_validation"
    }
    return cross_validation_rule_ids, cross_validation_config_paths


def _has_dq_signal(
    entry: RunLedgerEntry,
    *,
    rule_ids: set[str],
    dispositions: set[str],
    report_paths: set[str],
) -> bool:
    """Return whether a ledger entry carries any DQ signal."""
    return (
        entry.event_family == "dq"
        or entry.event_type.startswith("dq_")
        or bool(rule_ids)
        or bool(dispositions)
        or bool(report_paths)
    )


def _extract_dq_details(entry: RunLedgerEntry) -> DQDetailsSummary:
    """Extract DQ-oriented anchors from one ledger entry."""
    details = entry.details or {}
    rule_ids = _collect_dq_values(
        details,
        single_key="rule_id",
        collection_keys=("dq_rule_ids", "rule_ids"),
    )
    dispositions = _collect_dq_values(
        details,
        single_key="disposition",
        collection_keys=("dq_dispositions", "dispositions"),
    )
    report_paths = _collect_dq_values(details, single_key="dq_report_path")
    violation_kinds = _collect_dq_values(
        details,
        single_key="violation_kind",
        collection_keys=("violation_kinds",),
    )
    config_paths = _collect_dq_values(
        details,
        single_key="config_path",
        collection_keys=("config_paths",),
    )
    cross_validation_rule_ids, cross_validation_config_paths = (
        _extract_cross_validation_sets(rule_ids, config_paths)
    )
    has_cross_validation_signal = (
        bool(cross_validation_rule_ids)
        or "cross_validation_mismatch" in violation_kinds
        or bool(cross_validation_config_paths)
    )
    has_signal = _has_dq_signal(
        entry,
        rule_ids=rule_ids,
        dispositions=dispositions,
        report_paths=report_paths,
    )
    return {
        "rule_ids": rule_ids,
        "dispositions": dispositions,
        "report_paths": report_paths,
        "violation_kinds": violation_kinds,
        "cross_validation_rule_ids": cross_validation_rule_ids,
        "cross_validation_config_paths": cross_validation_config_paths,
        "has_signal": has_signal,
        "has_cross_validation_signal": has_cross_validation_signal,
    }


def _update_correlation_anchor_gaps(
    gap_counter: dict[str, int],
    entry: RunLedgerEntry,
) -> None:
    """Count missing correlation anchors for execution-critical ledger events."""
    event_family = entry.event_family or "diagnostic"
    if event_family == "diagnostic" and entry.event_type == "manifest_created":
        return
    if event_family not in {
        "pipeline.lifecycle",
        "pipeline.phase",
        "artifact",
        "dq",
        "checkpoint",
        "composite",
    }:
        return
    diagnostic = _extract_diagnostic_context(entry)
    if diagnostic.get("effective_config_hash") is None:
        gap_counter["effective_config_hash"] += 1
    if diagnostic.get("contract_ref") is None:
        gap_counter["contract_ref"] += 1
    if diagnostic.get("data_contract_version") is None:
        gap_counter["data_contract_version"] += 1
    if event_family in {"checkpoint", "composite"} and (
        diagnostic.get("composite_run_id") is None
    ):
        gap_counter["composite_run_id"] += 1


def _extract_diagnostic_context(entry: RunLedgerEntry) -> dict[str, object]:
    """Return normalized diagnostic anchor payload from ledger entry details."""
    details = entry.details or {}
    raw_diagnostic = details.get("_diagnostic")
    if not isinstance(raw_diagnostic, dict):
        return {}
    return {str(key): value for key, value in raw_diagnostic.items()}


def _load_str_collection(raw_value: object) -> set[str]:
    """Normalize list-like diagnostic payloads into string sets."""
    if not isinstance(raw_value, list):
        return set()
    return {str(item) for item in raw_value}


__all__ = ["build_diagnostics_summary"]
