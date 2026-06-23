"""Timeseries operations for quarantine records."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quarantine._statistics_helpers import (
    bucket_start_iso,
    resolve_bucket_seconds,
)
from bioetl.infrastructure.quarantine.filtered_reads import _load_filtered_rows


def get_filtered_timeseries(
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
    bucket: str = "1h",
) -> JsonDict:
    """Return time-bucketed Silver-filter aggregates for explorer trend panels."""
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
    bucket_seconds = resolve_bucket_seconds(bucket)
    buckets: dict[str, dict] = {}
    for row in rows:
        bucket_start = bucket_start_iso(
            row.get("ingestion_ts"),
            bucket_seconds=bucket_seconds,
        )
        if bucket_start is None:
            continue
        bucket_row = buckets.setdefault(
            bucket_start,
            {
                "bucket_start": bucket_start,
                "reject_count": 0,
                "bronze_records": 0,
                "reject_ratio": 0.0,
                "run_ids": set(),
            },
        )
        bucket_row["reject_count"] = int(bucket_row["reject_count"]) + 1
        run_id_value = row.get("run_id")
        if isinstance(run_id_value, str) and run_id_value.strip():
            bucket_row["run_ids"].add(run_id_value.strip())

    ordered_rows: list[dict] = []
    for bucket_start in sorted(buckets):
        bucket_row = buckets[bucket_start]
        bucket_row["run_ids"] = sorted(bucket_row["run_ids"])
        ordered_rows.append(bucket_row)
    return {
        "bucket": bucket.strip().lower(),
        "rows": ordered_rows,
    }
