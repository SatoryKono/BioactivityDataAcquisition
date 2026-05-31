"""Helper utilities for run manifest diagnostics extraction."""

from __future__ import annotations

from typing import TypedDict

from bioetl.domain.control_plane import RunLedgerEntry


class DQDetailsSummary(TypedDict):
    """Normalized DQ anchor sets extracted from one ledger entry."""

    rule_ids: set[str]
    dispositions: set[str]
    report_paths: set[str]
    violation_kinds: set[str]
    cross_validation_rule_ids: set[str]
    cross_validation_config_paths: set[str]
    cross_validation_quarantine_policies: set[str]
    cross_validation_replay_contracts: set[str]
    occurrence_only_diagnostic_scopes: set[str]
    has_signal: bool
    has_cross_validation_signal: bool


def collect_dq_values(
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
        values.update(load_str_collection(details.get(key)))
    return values


def extract_cross_validation_sets(
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


def has_dq_signal(
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


def extract_dq_details(entry: RunLedgerEntry) -> DQDetailsSummary:
    """Extract DQ-oriented anchors from one ledger entry."""
    details = entry.details or {}
    rule_ids = collect_dq_values(
        details,
        single_key="rule_id",
        collection_keys=("dq_rule_ids", "rule_ids"),
    )
    dispositions = collect_dq_values(
        details,
        single_key="disposition",
        collection_keys=("dq_dispositions", "dispositions"),
    )
    report_paths = collect_dq_values(details, single_key="dq_report_path")
    violation_kinds = collect_dq_values(
        details,
        single_key="violation_kind",
        collection_keys=("violation_kinds",),
    )
    config_paths = collect_dq_values(
        details,
        single_key="config_path",
        collection_keys=("config_paths",),
    )
    cross_validation_rule_ids, cross_validation_config_paths = (
        extract_cross_validation_sets(rule_ids, config_paths)
    )
    quarantine_policies = collect_dq_values(
        details,
        single_key="artifact_policy",
        collection_keys=("artifact_policies",),
    )
    replay_contracts = collect_dq_values(
        details,
        single_key="replay_contract",
        collection_keys=("replay_contracts",),
    )
    occurrence_only_diagnostic_scopes = collect_dq_values(
        details,
        single_key="diagnostic_scope",
        collection_keys=("diagnostic_scopes",),
    )
    has_cross_validation_signal = (
        bool(cross_validation_rule_ids)
        or "cross_validation_mismatch" in violation_kinds
        or bool(cross_validation_config_paths)
    )
    has_signal = has_dq_signal(
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
        "cross_validation_quarantine_policies": quarantine_policies,
        "cross_validation_replay_contracts": replay_contracts,
        "occurrence_only_diagnostic_scopes": occurrence_only_diagnostic_scopes,
        "has_signal": has_signal,
        "has_cross_validation_signal": has_cross_validation_signal,
    }


def update_correlation_anchor_gaps(
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
    diagnostic = extract_diagnostic_context(entry)
    required_anchors = {
        "resolved_config_hash": diagnostic.get("resolved_config_hash"),
        "effective_config_hash": diagnostic.get("effective_config_hash"),
        "contract_ref": diagnostic.get("contract_ref"),
        "contract_version": _extract_contract_version_anchor(diagnostic),
    }
    for anchor_name, anchor_value in required_anchors.items():
        if anchor_value is None:
            gap_counter[anchor_name] += 1
    if event_family in {"checkpoint", "composite"}:
        composite_run_id = diagnostic.get("composite_run_id")
        if composite_run_id is None:
            gap_counter["composite_run_id"] += 1


def extract_diagnostic_context(entry: RunLedgerEntry) -> dict[str, object]:
    """Return normalized diagnostic anchor payload from ledger entry details."""
    details = entry.details or {}
    raw_diagnostic = details.get("_diagnostic")
    if not isinstance(raw_diagnostic, dict):
        return {}
    return {str(key): value for key, value in raw_diagnostic.items()}


def _extract_contract_version_anchor(diagnostic: dict[str, object]) -> object | None:
    """Return canonical or legacy contract-version anchor from diagnostics."""
    if "contract_version" in diagnostic:
        return diagnostic.get("contract_version")
    return diagnostic.get("data_contract_version")


def load_str_collection(raw_value: object) -> set[str]:
    """Normalize list-like diagnostic payloads into string sets."""
    if not isinstance(raw_value, list):
        return set()
    return {str(item) for item in raw_value}


def build_dq_details_summary(
    *,
    rule_ids: set[str],
    dispositions: set[str],
    report_paths: set[str],
    violation_kinds: set[str],
    cross_validation_rule_ids: set[str],
    cross_validation_config_paths: set[str],
    cross_validation_quarantine_policies: set[str],
    cross_validation_replay_contracts: set[str],
    occurrence_only_diagnostic_scopes: set[str],
    has_signal: bool,
    has_cross_validation_signal: bool,
) -> DQDetailsSummary:
    """Build one normalized DQ anchor summary from ledger aggregation state."""
    return DQDetailsSummary(
        rule_ids=rule_ids,
        dispositions=dispositions,
        report_paths=report_paths,
        violation_kinds=violation_kinds,
        cross_validation_rule_ids=cross_validation_rule_ids,
        cross_validation_config_paths=cross_validation_config_paths,
        cross_validation_quarantine_policies=cross_validation_quarantine_policies,
        cross_validation_replay_contracts=cross_validation_replay_contracts,
        occurrence_only_diagnostic_scopes=occurrence_only_diagnostic_scopes,
        has_signal=has_signal,
        has_cross_validation_signal=has_cross_validation_signal,
    )


def build_dq_details_summary_kwargs(
    *,
    rule_ids: set[str],
    dispositions: set[str],
    report_paths: set[str],
    violation_kinds: set[str],
    cross_validation_rule_ids: set[str],
    cross_validation_config_paths: set[str],
    cross_validation_quarantine_policies: set[str],
    cross_validation_replay_contracts: set[str],
    occurrence_only_diagnostic_scopes: set[str],
    has_signal: bool,
    has_cross_validation_signal: bool,
) -> dict[str, object]:
    """Return reusable kwargs payload for DQ detail summary construction."""
    return {
        "rule_ids": rule_ids,
        "dispositions": dispositions,
        "report_paths": report_paths,
        "violation_kinds": violation_kinds,
        "cross_validation_rule_ids": cross_validation_rule_ids,
        "cross_validation_config_paths": cross_validation_config_paths,
        "cross_validation_quarantine_policies": cross_validation_quarantine_policies,
        "cross_validation_replay_contracts": cross_validation_replay_contracts,
        "occurrence_only_diagnostic_scopes": occurrence_only_diagnostic_scopes,
        "has_signal": has_signal,
        "has_cross_validation_signal": has_cross_validation_signal,
    }
