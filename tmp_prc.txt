"""Processed Records table payload helpers for dashboard HTTP surfaces."""

from __future__ import annotations

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.interfaces.http import _processed_records_table_support as _support

ProcessedRecordRowSpec = _support.ProcessedRecordRowSpec
PROCESSED_RECORDS_ROW_SPECS = _support.PROCESSED_RECORDS_ROW_SPECS
PROCESSED_RECORDS_TABLE_CONTRACT = _support.PROCESSED_RECORDS_TABLE_CONTRACT
DEFAULT_PROMETHEUS_BASE_URL = _support.DEFAULT_PROMETHEUS_BASE_URL
fetch_processed_record_values = _support.fetch_processed_record_values
read_processed_records_run_id = _support.read_processed_records_run_id
_processed_record_value_query = _support._processed_record_value_query

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


def build_processed_records_table_payload(
    *,
    metric_values: dict[str, float | int | None],
    pipeline: str,
    run_type: str | None,
) -> dict[str, object]:
    """Build the Grafana table payload from current accounting metric values."""
    rows: list[dict[str, object]] = []
    bronze_value = _support.as_float(metric_values.get(_BRONZE_METRIC))
    silver_valid_value = _support.as_float(metric_values.get(_SILVER_VALID_METRIC))
    silver_sum = _support.sum_metric_values(metric_values, _SILVER_METRICS)
    gold_sum = _support.sum_metric_values(metric_values, _GOLD_METRICS)
    silver_deficit = _support.is_deficit(total=silver_sum, minimum=bronze_value)
    gold_deficit = _support.is_deficit(total=gold_sum, minimum=silver_valid_value)
    value_width = (
        len(_support.count_text(bronze_value)) if bronze_value is not None else 0
    )

    for spec in PROCESSED_RECORDS_ROW_SPECS:
        raw_value = _support.as_float(metric_values.get(spec.metric))
        value_text = _support.padded_count_text(raw_value, value_width)
        percentage_text = _support.format_percentage(
            value=raw_value,
            bronze_value=bronze_value,
            denominator=spec.denominator,
            percent_format=spec.percent_format,
        )
        rows.append(
            {
                "parameter": spec.parameter,
                "value": _support.display_token(spec.parameter, value_text),
                # Canonical field name is ``percentage`` (PFILL-02; typo alias removed).
                "percentage": _support.display_token(
                    spec.parameter,
                    percentage_text,
                ),
                "row_status": _support.row_status(
                    parameter=spec.parameter,
                    silver_deficit=silver_deficit,
                    gold_deficit=gold_deficit,
                ),
            }
        )

    return {
        "contract": PROCESSED_RECORDS_TABLE_CONTRACT,
        "pipeline": pipeline,
        "run_type": list(_support.selector_tokens(run_type)),
        "rows": rows,
    }


def build_processed_records_table_payload_from_prometheus(
    *,
    prometheus_base_url: str,
    pipeline: str,
    run_type: str | None,
) -> dict[str, object]:
    """Fetch current accounting metrics and return the dashboard table payload."""
    if _support.is_unknown_scope(pipeline):
        metric_values: dict[str, float | int | None] = {
            spec.metric: None for spec in PROCESSED_RECORDS_ROW_SPECS
        }
        return build_processed_records_table_payload(
            metric_values=metric_values,
            pipeline=pipeline,
            run_type=run_type,
        )

    metric_values = fetch_processed_record_values(
        prometheus_base_url=prometheus_base_url,
        pipeline=pipeline,
        run_type=run_type,
    )
    return build_processed_records_table_payload(
        metric_values=metric_values,
        pipeline=pipeline,
        run_type=run_type,
    )


def build_processed_records_table_payload_from_ledger(
    *,
    ledger_entries: tuple[RunLedgerEntry, ...],
    pipeline: str,
    run_type: str | None,
) -> dict[str, object]:
    """Build exact-run accounting rows from RunLedger source-of-truth entries."""
    if not ledger_entries:
        return build_processed_records_table_payload(
            metric_values={spec.metric: None for spec in PROCESSED_RECORDS_ROW_SPECS},
            pipeline=pipeline,
            run_type=run_type,
        )

    metric_values: dict[str, float | int | None] = {
        spec.metric: 0 for spec in PROCESSED_RECORDS_ROW_SPECS
    }
    latest_snapshot = _support.latest_metrics_snapshot(ledger_entries)
    if latest_snapshot:
        metric_values.update(
            {
                "bioetl_processed_records_bronze_current": latest_snapshot.get(
                    "records_bronze",
                    0,
                ),
                "bioetl_processed_records_silver_valid_current": latest_snapshot.get(
                    "records_silver",
                    0,
                ),
                "bioetl_processed_records_silver_quarantined_current": (
                    latest_snapshot.get("records_quarantined", 0)
                ),
                "bioetl_processed_records_silver_filtered_out_current": (
                    latest_snapshot.get("records_filtered_out", 0)
                ),
                "bioetl_processed_records_gold_written_current": latest_snapshot.get(
                    "records_gold",
                    0,
                ),
                "bioetl_processed_records_gold_excluded_by_contract_current": (
                    latest_snapshot.get("records_gold_excluded_by_contract", 0)
                ),
            }
        )

    artifact_counts = _support.published_layer_artifact_counts(ledger_entries)
    silver_snapshot_count = (
        latest_snapshot.get("records_silver") if latest_snapshot is not None else None
    )
    silver_artifact_count = artifact_counts.get("silver")
    silver_deduplicated_count = 0
    if (
        isinstance(silver_snapshot_count, int)
        and isinstance(silver_artifact_count, int)
        and silver_snapshot_count >= silver_artifact_count
    ):
        silver_deduplicated_count = silver_snapshot_count - silver_artifact_count
    metric_values.update(
        {
            "bioetl_processed_records_bronze_current": artifact_counts.get(
                "bronze",
                metric_values["bioetl_processed_records_bronze_current"],
            ),
            "bioetl_processed_records_silver_valid_current": artifact_counts.get(
                "silver",
                metric_values["bioetl_processed_records_silver_valid_current"],
            ),
            "bioetl_processed_records_gold_written_current": artifact_counts.get(
                "gold",
                metric_values["bioetl_processed_records_gold_written_current"],
            ),
            "bioetl_processed_records_silver_deduplicated_current": (
                silver_deduplicated_count
            ),
        }
    )
    return build_processed_records_table_payload(
        metric_values=metric_values,
        pipeline=pipeline,
        run_type=run_type,
    )


__all__ = [
    "DEFAULT_PROMETHEUS_BASE_URL",
    "PROCESSED_RECORDS_ROW_SPECS",
    "PROCESSED_RECORDS_TABLE_CONTRACT",
    "ProcessedRecordRowSpec",
    "build_processed_records_table_payload",
    "build_processed_records_table_payload_from_ledger",
    "build_processed_records_table_payload_from_prometheus",
    "fetch_processed_record_values",
    "read_processed_records_run_id",
]
