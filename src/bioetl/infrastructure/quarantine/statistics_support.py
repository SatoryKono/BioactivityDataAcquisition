"""Pure helper functions for quarantine statistics aggregation."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quarantine.filtered_reads import (
    _build_reason_field_signature,
    _build_reason_signature,
    _increment_counter,
)

__all__ = [
    "_build_reason_signature_from_row",
    "_build_statistics_response",
    "_count_bronze_records",
    "_get_time_statistics",
    "_process_quarantine_records",
    "_scoped_pipeline_names",
    "_sorted_counter_items",
]


def _build_reason_signature_from_row(row: JsonDict) -> str:
    """Build a stable reason signature from one filtered row."""
    return " | ".join(
        str(row.get(key, "")).strip()
        for key in ("reason_code", "rule_type", "field", "operator")
        if isinstance(row.get(key), str) and str(row.get(key)).strip()
    )


def _scoped_pipeline_names(
    rows: list[JsonDict],
    pipeline_filter: set[str] | None,
) -> set[str]:
    """Resolve the pipeline scope used for bronze totals."""
    if pipeline_filter is not None:
        return set(pipeline_filter)
    return {
        row.get("pipeline", "").strip()
        for row in rows
        if isinstance(row.get("pipeline"), str) and row.get("pipeline", "").strip()
    }


def _count_bronze_records(
    rows: list[JsonDict],
    *,
    pipeline_filter: set[str] | None,
    pipeline_stats_loader: callable,
    run_id_single: str | None,
) -> int:
    """Sum bronze totals for the currently scoped pipelines."""
    bronze_records = 0
    for pipeline_name in sorted(_scoped_pipeline_names(rows, pipeline_filter)):
        stats = pipeline_stats_loader(pipeline_name, run_id_single)
        pipeline_total = stats.get("total_count")
        if isinstance(pipeline_total, int):
            bronze_records += pipeline_total
    return bronze_records


def _sorted_counter_items(counter: dict[str, int]) -> list[JsonDict]:
    """Return counter items sorted by descending frequency for API responses."""
    return [
        {"key": key, "count": value}
        for key, value in sorted(
            counter.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def _process_quarantine_records(
    records: list[dict],
) -> tuple[
    dict[str, int],
    dict[str, int],
    dict[str, int],
    dict[str, int],
    dict[str, int],
    dict[str, int],
    dict[str, int],
    dict[str, int],
    int,
]:
    """Process quarantine records and extract statistics."""
    by_error_code: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_reason_code: dict[str, int] = {}
    by_field: dict[str, int] = {}
    by_rule_type: dict[str, int] = {}
    by_operator: dict[str, int] = {}
    by_reason_code_field: dict[str, int] = {}
    by_reason_signature: dict[str, int] = {}
    silver_filter_total = 0

    for record in records:
        record_error_code = record["error_code"]
        status = record["dq_status"]
        by_error_code[record_error_code] = by_error_code.get(record_error_code, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        if record_error_code != "FILTERED_OUT_SILVER":
            continue
        silver_filter_total += 1
        error_details = _normalize_error_details(record)
        _increment_counter(by_reason_code, error_details.get("reason_code"))
        _increment_counter(by_field, error_details.get("field"))
        _increment_counter(by_rule_type, error_details.get("rule_type"))
        _increment_counter(by_operator, error_details.get("operator"))
        reason_field_signature = _build_reason_field_signature(error_details)
        if reason_field_signature:
            by_reason_code_field[reason_field_signature] = (
                by_reason_code_field.get(reason_field_signature, 0) + 1
            )
        reason_signature = _build_reason_signature(error_details)
        if reason_signature:
            by_reason_signature[reason_signature] = (
                by_reason_signature.get(reason_signature, 0) + 1
            )

    return (
        by_error_code,
        by_status,
        by_reason_code,
        by_field,
        by_rule_type,
        by_operator,
        by_reason_code_field,
        by_reason_signature,
        silver_filter_total,
    )


def _normalize_error_details(record: JsonDict) -> JsonDict:
    """Return structured error details for one quarantine row."""
    error_details = record.get("error_details")
    if isinstance(error_details, str):
        from bioetl.domain.serialization import deserialize_from_json

        decoded = deserialize_from_json(error_details)
        if isinstance(decoded, dict):
            return decoded
        return {}
    if isinstance(error_details, dict):
        return error_details
    return {}


def _get_time_statistics(
    arrow_table: object,
) -> tuple[object, object]:
    """Get oldest and newest record timestamps."""
    df_pandas = arrow_table.to_pandas()
    return df_pandas["ingestion_ts"].min(), df_pandas["ingestion_ts"].max()


def _build_statistics_response(
    total_records: int,
    by_error_code: dict[str, int],
    by_status: dict[str, int],
    oldest_record: object,
    newest_record: object,
    silver_filter_total: int,
    by_reason_code: dict[str, int],
    by_field: dict[str, int],
    by_rule_type: dict[str, int],
    by_operator: dict[str, int],
    by_reason_code_field: dict[str, int],
    by_reason_signature: dict[str, int],
) -> JsonDict:
    """Build the final statistics response."""
    return {
        "total_count": total_records,
        "total_records": total_records,
        "by_error_code": by_error_code,
        "by_status": by_status,
        "oldest_record": oldest_record,
        "newest_record": newest_record,
        "silver_filter_rejects": {
            "total_count": silver_filter_total,
            "by_reason_code": by_reason_code,
            "by_field": by_field,
            "by_rule_type": by_rule_type,
            "by_operator": by_operator,
            "by_reason_code_field": by_reason_code_field,
            "by_reason_signature": by_reason_signature,
        },
    }
