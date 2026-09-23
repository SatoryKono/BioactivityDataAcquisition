"""Recent launch index combining persisted reports and control-plane evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from bioetl.application.runtime_clock import current_utc_time
from bioetl.domain.ports import RunManifestPort
from bioetl.interfaces.http._control_plane_selector_records import (
    RunLedgerLookup,
    SelectorRecord,
    build_selector_records,
    narrow_manifest_catalog,
)
from bioetl.interfaces.http.run_report_ops import (
    _normalize_list_owner,
    _validated_artifact_paths,
    list_pipeline_run_report_payloads,
)

REPORT_MISSING = "REPORT MISSING"
_TERMINAL_STATUSES = frozenset(
    {"success", "failed", "fail", "partial", "shutdown", "dry_run"}
)


def _timestamp(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return (
        parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    )


def _scope(value: str | None) -> tuple[str, ...]:
    return tuple(
        token
        for part in (value or "").split(",")
        if (token := _normalize_list_owner(part)) is not None
    )


def _catalog_status(*, started: bool, terminal: bool, run_status: object) -> str:
    if terminal:
        return str(run_status)
    if started:
        return "unfinished"
    return "unknown"


def _catalog_row(record: SelectorRecord) -> dict[str, object]:
    """A started event is the last known state, not a live-process health probe."""
    started = record.started_at_source == "run_ledger_started_event"
    terminal = record.terminal_event_type is not None
    processing_status = _catalog_status(
        started=started, terminal=terminal, run_status=record.run_status
    )
    return {
        "pipeline": record.pipeline,
        "run_id": record.run_id,
        "workflow_id": _workflow_name(record),
        "workflow_run_id": "—",
        "run_type": record.run_type,
        "started_at": record.started_at.isoformat(),
        "started_at_source": record.started_at_source,
        "completed_at": record.completed_at.isoformat() if terminal else None,
        "status": processing_status,
        "processing_status": processing_status,
        "trust_status": "UNKNOWN",
        "report_state": REPORT_MISSING,
        "selected": 0,
        "json_path": None,
        "markdown_path": None,
        "last_event_at": record.last_event_at.isoformat()
        if record.last_event_at
        else None,
    }


def _workflow_name(record: SelectorRecord) -> str:
    # The selector resolver also synthesizes pipeline aliases. Do not present
    # those aliases as evidence of an actual parent workflow occurrence.
    for payload in (
        record.manifest.launch_context,
        record.manifest.runtime_config,
        record.manifest.resolved_config,
    ):
        for key in ("workflow_name", "workflow"):
            if value := payload.get(key):
                return str(value)
    return "—"


def _merge_record(row: dict[str, object], record: SelectorRecord) -> dict[str, object]:
    catalog = _catalog_row(record)
    if not row:
        return catalog
    merged = {**catalog, **row, "report_state": "AVAILABLE"}
    if record.started_at_source == "run_ledger_started_event" or not row.get(
        "started_at"
    ):
        merged["started_at"] = catalog["started_at"]
        merged["started_at_source"] = catalog["started_at_source"]
    return merged


def _merge_catalog_rows(
    rows: dict[tuple[str, str], dict[str, object]],
    *,
    manifest_port: RunManifestPort,
    ledger_port: RunLedgerLookup | None,
    pipelines: tuple[str, ...],
    run_types: tuple[str, ...],
) -> None:
    try:
        manifests = narrow_manifest_catalog(
            manifest_port.list_all(),
            selected_pipelines=pipelines,
            selected_workflows=(),
            selected_run_types=run_types,
            selected_run_id=None,
            fail_open_when_empty=False,
        )
        for manifest in manifests:
            key = (manifest.pipeline_name, str(manifest.run_id))
            report = rows.get(key, {})
            # Final reports already contain immutable start/status evidence.
            # Read ledger history only for missing/incomplete reports, avoiding
            # an expensive full-history scan on every fleet refresh.
            lookup = None if _has_terminal_identity(report) else ledger_port
            record = build_selector_records((manifest,), lookup)[0]
            rows[key] = _merge_record(report, record)
    except OSError as exc:
        raise RuntimeError("Recent launch catalog could not be read") from exc


def _row_matches_scope(
    row: dict[str, object],
    *,
    workflows: tuple[str, ...],
    run_types: tuple[str, ...],
    lookup_run_id: str,
) -> bool:
    if workflows and row.get("workflow_id") not in workflows:
        return False
    if run_types and row.get("run_type") not in run_types:
        return False
    return not lookup_run_id or row["run_id"] == lookup_run_id


def _workflow_scope(row: dict[str, object]) -> str:
    workflow_id = row.get("workflow_id")
    if workflow_id in {None, "", "—"}:
        return "$__all"
    return str(workflow_id)


def list_recent_pipeline_runs(
    *,
    pipeline: str | None,
    workflow: str | None,
    run_type: str | None,
    selected_run_id: str | None,
    limit: int,
    manifest_port: RunManifestPort | None,
    ledger_port: RunLedgerLookup | None,
    root: Path | None = None,
    lookup_run_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Filter and rank all identities before taking one global bounded page.

    Retention/CLI listing keeps its existing mtime ordering. Report previews
    remain the source for orphan reports; the catalog adds unfinished runs.
    """
    payload: dict[str, object] = list_pipeline_run_report_payloads(
        pipeline_name=pipeline,
        limit=None,
        root=root,
        selected_run_id=selected_run_id,
    )
    if payload["index_state"] not in {"ok", "valid_empty"}:
        return payload
    if manifest_port is None:
        raise RuntimeError(
            "Recent launch catalog unavailable: manifest port is not configured"
        )
    rows = {
        (str(item["pipeline"]), str(item["run_id"])): {
            **item,
            "report_state": "AVAILABLE",
            "started_at_source": "report_identity",
        }
        for item in _report_rows(payload)
    }
    pipelines, workflows, run_types = (
        _scope(pipeline),
        _scope(workflow),
        _scope(run_type),
    )
    _merge_catalog_rows(
        rows,
        manifest_port=manifest_port,
        ledger_port=ledger_port,
        pipelines=pipelines,
        run_types=run_types,
    )
    lookup_run_id = (lookup_run_id or "").strip()
    items = [
        row
        for row in rows.values()
        if _row_matches_scope(
            row,
            workflows=workflows,
            run_types=run_types,
            lookup_run_id=lookup_run_id,
        )
    ]
    items.sort(
        key=lambda row: (
            _timestamp(row.get("started_at")),
            str(row["pipeline"]),
            str(row["run_id"]),
        ),
        reverse=True,
    )
    items = items[:limit]
    observed_at = now or current_utc_time()
    for item in items:
        item.update(_report_link(item, root))
        item.update(_timing_fields(item, observed_at))
        run_identity = str(item["run_id"])
        item["run_label"] = (
            run_identity[:8] + "…" + run_identity[-4:]
            if len(run_identity) > 16
            else run_identity
        )
        item["selected"] = int(item["run_id"] == selected_run_id)
        item["workflow_scope"] = _workflow_scope(item)
    return {
        **payload,
        "items": items,
        "count": len(items),
        "index_state": "ok" if items else "valid_empty",
        "index_state_message": "Latest launches by started_at; manifest creation is the explicit fallback.",
        "catalog_state": "available" if manifest_port is not None else "unavailable",
        "order_by": "started_at_desc",
    }


def _round_nonneg_half_up(value: float) -> int:
    """Round a non-negative value half away from zero (not banker's rounding)."""
    return int(value + 0.5)


def _format_compact_duration(seconds: float) -> str:
    """Format a non-negative age as compact duration with spaced units."""
    total = max(0, _round_nonneg_half_up(seconds))
    hours, remainder = divmod(total, 3600)
    if hours:
        minutes = _round_nonneg_half_up(remainder / 60)
        if minutes == 60:
            hours += 1
            minutes = 0
        if minutes:
            return f"{hours} h {minutes} m"
        return f"{hours} h"
    minutes, secs = divmod(remainder, 60)
    if minutes and secs:
        return f"{minutes} m {secs} s"
    if minutes:
        return f"{minutes} m"
    return f"{secs} s"


def _event_age_display(
    row: dict[str, object], now: datetime, last: datetime, minimum: datetime
) -> str:
    if row.get("status") in _TERMINAL_STATUSES:
        last = _timestamp(row.get("completed_at"))
    if minimum < last <= now:
        return _format_compact_duration((now - last).total_seconds())
    return "UNKNOWN"


def _timing_fields(row: dict[str, object], now: datetime) -> dict[str, object]:
    """Use event timestamps, never file mtime or scrape time, for elapsed values."""
    minimum = datetime.min.replace(tzinfo=UTC)
    start, end = _timestamp(row.get("started_at")), _timestamp(row.get("completed_at"))
    last = _timestamp(row.get("last_event_at"))
    duration = None
    if start != minimum and end >= start and end != minimum:
        duration = (end - start).total_seconds()
    last_event_age = None
    event = end if row.get("status") in _TERMINAL_STATUSES else last
    if minimum < event <= now:
        last_event_age = (now - event).total_seconds()
    return {
        "duration_seconds": duration,
        "duration_display": (
            _format_compact_duration(duration) if duration is not None else None
        ),
        "last_event_age_seconds": last_event_age,
        "event_age_display": _event_age_display(row, now, last, minimum),
    }


def _report_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    items = payload.get("items")
    if not isinstance(items, list):
        raise RuntimeError("Run report index returned invalid items")
    return [dict(item) for item in items if isinstance(item, dict)]


def _report_link(row: dict[str, object], root: Path | None) -> dict[str, object]:
    """Bind a file link to one row; recheck files only for the bounded page."""
    missing: dict[str, object] = {
        "report_url": "",
        "report_format": None,
        "report_label": REPORT_MISSING,
        "report_state": REPORT_MISSING,
    }
    pipeline, run_id = str(row["pipeline"]), str(row["run_id"])
    try:
        json_path, markdown_path = _validated_artifact_paths(
            pipeline, run_id, "pipeline_run_report_md", root
        )
    except ValueError:
        return missing
    available = bool(row.get("json_path")) and json_path.is_file()
    report_format = (
        "pipeline_run_report_md"
        if available and markdown_path.is_file()
        else "pipeline_run_report_json"
    )
    query = urlencode({"pipeline": pipeline, "run_id": run_id, "format": report_format})
    url = (
        "/api/datasources/proxy/uid/bioetl-ops-http/ops/observability/"
        f"pipeline-run-report-artifact?{query}"
    )
    if not available:
        # Grafana 12 applies links to an entire column. A missing report links
        # to its exact lookup and explicit 404, never an empty/current-page URL.
        return {**missing, "report_url": url}
    return {
        "report_url": url,
        "report_format": report_format,
        "report_label": "Open report",
        "report_state": "AVAILABLE",
    }


def _has_terminal_identity(row: dict[str, object]) -> bool:
    return (
        _timestamp(row.get("started_at")) != datetime.min.replace(tzinfo=UTC)
        and row.get("status") in _TERMINAL_STATUSES
    )
