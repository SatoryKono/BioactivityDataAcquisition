"""Filtered helper utilities for :mod:`_quarantine_service_filtered_mixin`.

Keeping denominator and scope-resolution logic in a dedicated module keeps the
application mixin layer under the file-size policy while preserving behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
)
from bioetl.domain.types import JsonDict

_QUARANTINE_OPERATOR_ERRORS = (OSError, RuntimeError, TypeError, ValueError)
_ALL_SCOPE_TOKENS = {"", "*", "all", "$__all", "__all"}
_TERMINAL_EVENT_TYPES = frozenset(
    {RUN_FINISHED_EVENT, RUN_FAILED_EVENT, RUN_SHUTDOWN_EVENT}
)


def _resolve_bronze_records_from_inspection(inspection: object) -> int | None:
    """Return one run-scoped Bronze denominator from manifest ledger entries."""
    bronze_records: int | None = None
    for entry in getattr(inspection, "ledger_entries", ()):
        metrics_snapshot = getattr(entry, "metrics_snapshot", None)
        if not isinstance(metrics_snapshot, dict):
            continue
        value = metrics_snapshot.get("records_bronze")
        if not isinstance(value, int) or value <= 0:
            continue
        bronze_records = value if bronze_records is None else max(bronze_records, value)
    return bronze_records


def _resolve_bronze_records_from_entries(entries: object) -> int | None:
    """Return one run-scoped Bronze denominator from raw ledger entries."""
    bronze_records: int | None = None
    for entry in entries if isinstance(entries, list | tuple) else ():
        metrics_snapshot = getattr(entry, "metrics_snapshot", None)
        if not isinstance(metrics_snapshot, dict):
            continue
        value = metrics_snapshot.get("records_bronze")
        if not isinstance(value, int) or value <= 0:
            continue
        bronze_records = value if bronze_records is None else max(bronze_records, value)
    return bronze_records


def _parse_scope_tokens(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    tokens = tuple(
        token
        for token in (
            candidate.strip()
            for candidate in str(value).replace("{", "").replace("}", "").split(",")
        )
        if token and token.lower() not in _ALL_SCOPE_TOKENS
    )
    return tokens


def _resolve_filtered_stats_run_ids(
    *,
    run_id: str | None,
    scoped_run_ids: object,
    pipeline: str | None,
    run_type: str | None,
    run_manifest_service: object,
) -> list[str]:
    """Resolve unique run identifiers used to derive Bronze denominators."""
    if run_id is not None:
        return [run_id]
    if isinstance(scoped_run_ids, list) and scoped_run_ids:
        return [
            candidate
            for candidate in scoped_run_ids
            if isinstance(candidate, str) and candidate.strip()
        ]

    resolved_scope_run_id = _resolve_latest_scope_run_id(
        pipeline=pipeline,
        run_type=run_type,
        run_manifest_service=run_manifest_service,
    )
    return [resolved_scope_run_id] if resolved_scope_run_id is not None else []


def _latest_terminal_timestamp(
    *, run_id: object, ledger_port: object
) -> datetime | None:
    list_entries_by_run_id = getattr(ledger_port, "list_entries_by_run_id", None)
    if not callable(list_entries_by_run_id):
        return None
    from collections.abc import Iterable
    from typing import Any, cast

    listed = cast(
        Iterable[Any],  # Any: optional ledger extension has no return contract.
        list_entries_by_run_id(run_id),
    )
    entries = [
        entry
        for entry in listed
        if getattr(entry, "event_type", None) in _TERMINAL_EVENT_TYPES
    ]
    if not entries:
        return None
    latest_entry = max(
        entries,
        key=lambda entry: (
            _as_utc_datetime(getattr(entry, "occurred_at", None)),
            getattr(entry, "entry_id", ""),
        ),
    )
    occurred_at = getattr(latest_entry, "occurred_at", None)
    return _as_utc_datetime(occurred_at) if isinstance(occurred_at, datetime) else None


def _as_utc_datetime(value: object) -> datetime:
    """Normalize comparable timestamps and provide an aware minimum sentinel."""
    if not isinstance(value, datetime):
        return datetime.min.replace(tzinfo=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _manifest_matches_scope(
    *,
    manifest: object,
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
) -> bool:
    """Check whether a manifest belongs to requested scope and run types."""
    if getattr(manifest, "pipeline_name", None) not in selected_pipelines:
        return False
    if not selected_run_types:
        return True

    run_type_raw = getattr(manifest, "run_type", None)
    run_type_value = str(
        getattr(
            run_type_raw,
            "value",
            run_type_raw,
        )
    )
    return run_type_value in selected_run_types


def _pick_latest_scope_manifest(
    *,
    candidates: tuple[object, ...],
    run_manifest_service: object,
) -> object | None:
    """Pick most recent scope manifest based on terminal timestamp and run id."""
    if not candidates:
        return None

    ledger_port = getattr(run_manifest_service, "ledger_port", None)
    return max(
        candidates,
        key=lambda manifest: (
            _latest_terminal_timestamp(
                run_id=getattr(manifest, "run_id", None),
                ledger_port=ledger_port,
            )
            or _as_utc_datetime(getattr(manifest, "created_at", None)),
            str(getattr(manifest, "run_id", "")),
        ),
    )


def _resolve_latest_scope_run_id(
    *,
    pipeline: str | None,
    run_type: str | None,
    run_manifest_service: object,
) -> str | None:
    manifest_port = getattr(run_manifest_service, "manifest_port", None)
    if manifest_port is None or not hasattr(manifest_port, "list_all"):
        return None

    selected_pipelines = _parse_scope_tokens(pipeline)
    if len(selected_pipelines) != 1:
        return None
    selected_run_types = _parse_scope_tokens(run_type)

    manifests = tuple(manifest_port.list_all())
    candidates = tuple(
        manifest
        for manifest in manifests
        if _manifest_matches_scope(
            manifest=manifest,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
        )
    )
    if not candidates:
        return None

    selected_manifest = _pick_latest_scope_manifest(
        candidates=candidates,
        run_manifest_service=run_manifest_service,
    )
    if selected_manifest is None:
        return None
    run_id_value = getattr(selected_manifest, "run_id", None)
    return str(run_id_value) if run_id_value is not None else None


def _lookup_run_id(candidate_run_id: str) -> object:
    try:
        return UUID(candidate_run_id)
    except (TypeError, ValueError):
        return candidate_run_id


def _resolve_bronze_for_run(
    candidate_run_id: str,
    *,
    list_entries_by_run_id: object,
    run_manifest_service: object,
) -> int | None:
    if callable(list_entries_by_run_id):
        try:
            list_entries = cast(
                Callable[..., Any],  # Any: duck-typed host method after callable()
                list_entries_by_run_id,
            )
            resolved = _resolve_bronze_records_from_entries(
                list_entries(_lookup_run_id(candidate_run_id))
            )
        except (TypeError, ValueError):
            resolved = None
        else:
            if resolved is not None:
                return resolved
    show_manifest = getattr(run_manifest_service, "show", None)
    if not callable(show_manifest):
        return None
    try:
        show = cast(
            Callable[..., Any],  # Any: duck-typed host method after callable()
            show_manifest,
        )
        inspection = show(candidate_run_id)
    except ValueError:
        return None
    return _resolve_bronze_records_from_inspection(inspection)


def _sum_bronze_records_for_runs(
    *,
    run_ids: list[str],
    run_manifest_service: object,
) -> int:
    """Sum resolved Bronze record counts across the selected runs."""
    bronze_records = 0
    ledger_port = getattr(run_manifest_service, "ledger_port", None)
    list_entries_by_run_id = getattr(ledger_port, "list_entries_by_run_id", None)
    for candidate_run_id in sorted(set(run_ids)):
        resolved = _resolve_bronze_for_run(
            candidate_run_id,
            list_entries_by_run_id=list_entries_by_run_id,
            run_manifest_service=run_manifest_service,
        )
        if resolved is not None:
            bronze_records += resolved
    return bronze_records


def _enrich_filtered_stats_with_bronze_denominator(
    stats: JsonDict,
    *,
    pipeline: str | None,
    run_type: str | None,
    run_id: str | None,
    run_manifest_service: object,
) -> JsonDict:
    """Attach a bounded Bronze denominator when manifest evidence is available."""
    enriched = dict(stats)
    scoped_run_ids = enriched.pop("run_ids", None)
    if run_manifest_service is None:
        return enriched

    resolved_run_ids = _resolve_filtered_stats_run_ids(
        run_id=run_id,
        scoped_run_ids=scoped_run_ids,
        pipeline=pipeline,
        run_type=run_type,
        run_manifest_service=run_manifest_service,
    )
    bronze_records = _sum_bronze_records_for_runs(
        run_ids=resolved_run_ids,
        run_manifest_service=run_manifest_service,
    )
    if bronze_records <= 0:
        return enriched

    total = enriched.get("total", 0)
    enriched["bronze_records"] = bronze_records
    enriched["reject_ratio"] = (
        float(total / bronze_records) if isinstance(total, int) and total > 0 else 0.0
    )
    return enriched


def _reject_ratio(reject_count: object, bronze_records: int) -> float:
    """Calculate a bounded reject ratio for positive integer reject counts."""
    if isinstance(reject_count, int) and reject_count > 0:
        return float(reject_count / bronze_records)
    return 0.0


def _filtered_timeseries_run_ids(row: JsonDict) -> list[str]:
    """Remove and normalize run ids carried by the storage aggregation layer."""
    return [
        candidate
        for candidate in row.pop("run_ids", [])
        if isinstance(candidate, str) and candidate.strip()
    ]


def _enrich_filtered_timeseries_row(
    item: JsonDict,
    *,
    run_manifest_service: object,
) -> JsonDict:
    """Attach Bronze denominator evidence to one timeseries row when available."""
    enriched_row = dict(item)
    run_ids = _filtered_timeseries_run_ids(enriched_row)
    if run_manifest_service is None or not run_ids:
        return enriched_row

    bronze_records = _sum_bronze_records_for_runs(
        run_ids=run_ids,
        run_manifest_service=run_manifest_service,
    )
    if bronze_records <= 0:
        return enriched_row

    enriched_row["bronze_records"] = bronze_records
    enriched_row["reject_ratio"] = _reject_ratio(
        enriched_row.get("reject_count", 0),
        bronze_records,
    )
    return enriched_row


def _enrich_filtered_timeseries_with_bronze_denominators(
    payload: JsonDict,
    *,
    run_manifest_service: object,
) -> JsonDict:
    """Attach per-bucket Bronze denominators when manifest evidence is available."""
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return payload

    enriched_payload = dict(payload)
    enriched_rows: list[JsonDict] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        enriched_rows.append(
            _enrich_filtered_timeseries_row(
                item,
                run_manifest_service=run_manifest_service,
            )
        )

    enriched_payload["rows"] = enriched_rows
    return enriched_payload
