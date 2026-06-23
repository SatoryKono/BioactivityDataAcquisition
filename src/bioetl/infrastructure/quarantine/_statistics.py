"""Statistics operations for quarantine records."""

from __future__ import annotations

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quarantine._pyarrow_helpers import equal_mask
from bioetl.infrastructure.quarantine.filtered_reads import (
    _increment_counter,
    _load_filtered_rows,
    _single_filter_value,
)
from bioetl.infrastructure.quarantine.statistics_support import (
    _build_reason_signature_from_row,
    _build_statistics_response,
    _get_time_statistics,
    _process_quarantine_records,
    _sorted_counter_items,
)


def get_filtered_stats(
    base_path: str,
    storage_options: dict[str, str] | None,
    *,
    pipeline: str | None = None,
    run_type: str | None = None,
    reason_code: str | None = None,
    field: str | None = None,
    run_id: str | None = None,
    payload_hash: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
) -> JsonDict:
    """Return aggregate stats for filtered records under current scope."""
    rows = _load_filtered_rows(
        base_path,
        storage_options,
        pipeline=pipeline,
        run_type=run_type,
        reason_code=reason_code,
        field=field,
        run_id=run_id,
        payload_hash=payload_hash,
        from_ts=from_ts,
        to_ts=to_ts,
        include_payload=False,
        include_payload_preview=False,
    )
    by_reason_code: dict[str, int] = {}
    by_field: dict[str, int] = {}
    by_reason_signature: dict[str, int] = {}
    for row in rows:
        _increment_counter(by_reason_code, row.get("reason_code"))
        _increment_counter(by_field, row.get("field"))
        signature = _build_reason_signature_from_row(row)
        if signature:
            by_reason_signature[signature] = by_reason_signature.get(signature, 0) + 1

    total = len(rows)
    scoped_run_ids = sorted(
        {
            candidate
            for candidate in (row.get("run_id") for row in rows)
            if isinstance(candidate, str) and candidate.strip()
        }
    )
    if not scoped_run_ids:
        run_id_single = _single_filter_value(run_id)
        if run_id_single is not None:
            scoped_run_ids = [run_id_single]
    return {
        "total": total,
        "by_reason_code": _sorted_counter_items(by_reason_code),
        "by_field": _sorted_counter_items(by_field),
        "by_reason_signature": _sorted_counter_items(by_reason_signature),
        "bronze_records": 0,
        "reject_ratio": 0.0,
        "run_ids": scoped_run_ids,
    }


def get_statistics(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    error_code: str | None = None,
    run_id: str | None = None,
) -> JsonDict:
    """Get quarantine statistics for a pipeline.

    Args:
        base_path: Base directory path.
        storage_options: Storage options.
        pipeline: Pipeline.

    Returns:
        Statistics.
    """
    empty_stats = {
        "total_count": 0,
        "total_records": 0,
        "by_error_code": {},
        "by_status": {},
        "oldest_record": None,
        "newest_record": None,
        "silver_filter_rejects": {
            "total_count": 0,
            "by_reason_code": {},
            "by_field": {},
            "by_rule_type": {},
            "by_operator": {},
            "by_reason_code_field": {},
            "by_reason_signature": {},
        },
    }

    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return empty_stats

    filters: list[tuple[str, str, object]] = []
    if error_code:
        filters.append(("error_code", "=", error_code))
    arrow_table = dt.to_pyarrow_table(
        partitions=[("pipeline", "=", pipeline)],
        filters=filters or None,
    )
    if len(arrow_table) == 0:
        return empty_stats
    if run_id:
        arrow_table = arrow_table.filter(equal_mask(arrow_table["run_id"], run_id))
        if len(arrow_table) == 0:
            return empty_stats

    df = arrow_table.to_pylist()
    total_records = len(df)

    (
        by_error_code,
        by_status,
        by_reason_code,
        by_field,
        by_rule_type,
        by_operator,
        by_reason_code_field,
        by_reason_signature,
        silver_filter_total,
    ) = _process_quarantine_records(df)

    oldest_record, newest_record = _get_time_statistics(arrow_table)

    return _build_statistics_response(
        total_records,
        by_error_code,
        by_status,
        oldest_record,
        newest_record,
        silver_filter_total,
        by_reason_code,
        by_field,
        by_rule_type,
        by_operator,
        by_reason_code_field,
        by_reason_signature,
    )
