"""Translate saved-run accounting evidence into processed-record metrics."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.run_reports.accounting_projections import (
    REPORT_LAYER_FIELDS,
    reconcile_saved_layer_counts,
)
from bioetl.interfaces.http._processed_records_table_support import (
    PROCESSED_RECORDS_ROW_SPECS,
)
from bioetl.interfaces.http._processed_records_value_support import _selector_tokens

_REPORT_METRICS = {
    field: spec.metric
    for field, spec in zip(
        REPORT_LAYER_FIELDS, PROCESSED_RECORDS_ROW_SPECS, strict=True
    )
}


def fill_report_accounting(
    values: dict[str, float | int | None],
    *,
    report: Mapping[str, object] | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
    pipeline: str,
    run_type: str | None,
) -> None:
    """Translate complete, validated report counts to metric keys."""
    if not ledger_entries:
        return
    current = ledger_entries[-1]
    if any(entry.run_id != current.run_id for entry in ledger_entries):
        return
    observed = reconcile_saved_layer_counts(
        report,
        run_id=str(current.run_id),
        manifest_id=current.manifest_id,
        pipeline=pipeline,
        run_types=_selector_tokens(run_type),
        known_counts={
            field: values.get(metric) for field, metric in _REPORT_METRICS.items()
        },
    )
    values.update({_REPORT_METRICS[field]: value for field, value in observed.items()})
