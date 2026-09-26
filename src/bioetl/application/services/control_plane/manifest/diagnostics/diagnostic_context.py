"""Diagnostic context extraction helpers for run-manifest ledger entries."""

from __future__ import annotations

from bioetl.domain.control_plane import RunLedgerEntry


def update_correlation_anchor_gaps(
    gap_counter: dict[str, int],
    entry: RunLedgerEntry,
) -> None:
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
    details = entry.details or {}
    raw_diagnostic = details.get("_diagnostic")
    if not isinstance(raw_diagnostic, dict):
        return {}
    return {str(key): value for key, value in raw_diagnostic.items()}


def _extract_contract_version_anchor(diagnostic: dict[str, object]) -> object | None:
    if "contract_version" in diagnostic:
        return diagnostic.get("contract_version")
    return diagnostic.get("data_contract_version")
