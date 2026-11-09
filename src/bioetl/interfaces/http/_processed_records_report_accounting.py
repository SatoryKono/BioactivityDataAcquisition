"""Report-backed Processed Records accounting fills for legacy ledger gaps."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.interfaces.http._processed_records_value_support import _selector_tokens

_BRONZE_METRIC = "bioetl_processed_records_bronze_current"
_SILVER_VALID_METRIC = "bioetl_processed_records_silver_valid_current"
_SILVER_METRICS = (
    "bioetl_processed_records_silver_valid_current",
    "bioetl_processed_records_silver_filtered_out_current",
    "bioetl_processed_records_silver_quarantined_current",
    "bioetl_processed_records_silver_skipped_current",
    "bioetl_processed_records_silver_deduplicated_current",
)
_GOLD_METRICS = (
    "bioetl_processed_records_gold_written_current",
    "bioetl_processed_records_gold_excluded_by_contract_current",
    "bioetl_processed_records_gold_quarantined_current",
    "bioetl_processed_records_gold_skipped_current",
    "bioetl_processed_records_gold_deduplicated_current",
)
_REPORT_LAYER_FIELDS = (
    "bronze_records",
    "silver_valid",
    "silver_filtered_out",
    "silver_quarantined",
    "silver_skipped",
    "silver_deduplicated",
    "gold_written",
    "gold_excluded_by_contract",
    "gold_quarantined",
    "gold_skipped",
    "gold_deduplicated",
)


def _report_identity_matches(
    identity: Mapping[str, object],
    *,
    ledger_entries: tuple[RunLedgerEntry, ...],
    pipeline: str,
    run_type: str | None,
) -> bool:
    """Return True when report identity matches the validated ledger chain."""
    scopes = _selector_tokens(run_type)
    if identity.get("pipeline_name") != pipeline:
        return False
    if scopes and identity.get("run_type") not in scopes:
        return False
    if any(str(entry.run_id) != identity.get("run_id") for entry in ledger_entries):
        return False
    # A resumed run includes predecessor manifests; the report belongs to
    # the current (last) manifest in the validated ledger chain.
    return ledger_entries[-1].manifest_id == identity.get("manifest_id")


def _observed_layer_counts(
    layers: Mapping[str, object],
    values: Mapping[str, float | int | None],
) -> dict[str, int] | None:
    """Collect non-negative layer counts that do not conflict with known values."""
    # Local import avoids a cycle with `_processed_records_table_support`.
    from bioetl.interfaces.http._processed_records_table_support import (
        PROCESSED_RECORDS_ROW_SPECS,
    )

    observed: dict[str, int] = {}
    for spec, field in zip(
        PROCESSED_RECORDS_ROW_SPECS, _REPORT_LAYER_FIELDS, strict=True
    ):
        count = layers.get(field)
        if type(count) is not int or count < 0:
            return None
        existing = values.get(spec.metric)
        if existing is not None and existing != count:
            return None
        observed[spec.metric] = count
    return observed


def _layer_counts_balanced(observed: Mapping[str, int]) -> bool:
    """Reject incomplete accounting instead of manufacturing healthy zeros."""
    silver_total = sum(observed[key] for key in _SILVER_METRICS)
    gold_total = sum(observed[key] for key in _GOLD_METRICS)
    return (
        silver_total == observed[_BRONZE_METRIC]
        and gold_total == observed[_SILVER_VALID_METRIC]
    )


def fill_report_accounting(
    values: dict[str, float | int | None],
    *,
    report: Mapping[str, object] | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
    pipeline: str,
    run_type: str | None,
) -> None:
    """Fill legacy ledger gaps only from consistent, fully tracked run evidence."""
    if not report or report.get("tracking_coverage") != "full" or not ledger_entries:
        return
    identity, layers = report.get("identity"), report.get("layers")
    if not isinstance(identity, dict) or not isinstance(layers, dict):
        return
    if not _report_identity_matches(
        identity,
        ledger_entries=ledger_entries,
        pipeline=pipeline,
        run_type=run_type,
    ):
        return
    observed = _observed_layer_counts(layers, values)
    if observed is None or not _layer_counts_balanced(observed):
        return
    values.update(observed)
