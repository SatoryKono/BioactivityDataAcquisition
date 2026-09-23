"""Supplement selector catalogs with identity-checked persisted run reports."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from bioetl.application.services.run_reports.query import (
    ReportIndexEntry,
    list_pipeline_reports,
)
from bioetl.composition.observability_runtime import create_run_report_store
from bioetl.interfaces.http._identity_display_rows import format_timestamp_label
from bioetl.interfaces.http.report_root_config import configured_report_root
from bioetl.interfaces.http.run_report_ops import load_pipeline_run_report_payload

_FIELDS = {
    "workflow": "workflow_id",
    "pipeline": "pipeline_name",
    "run_type": "run_type",
    "run_id": "run_id",
    "run_status": "status",
    "provider": "provider",
}
_ALL = {"", "All", "all", "$__all", ".*"}
_CATALOG_READ_WORKERS = 4


def _allowed_scope(values: tuple[str, ...]) -> set[str]:
    return set(values) - _ALL


def _entry_matches_catalog(
    entry: ReportIndexEntry, scopes: dict[str, tuple[str, ...]]
) -> bool:
    pipelines = _allowed_scope(scopes.get("pipeline", ()))
    run_ids = _allowed_scope(scopes.get("run_id", ()))
    if pipelines and entry.owner not in pipelines:
        return False
    return not run_ids or entry.run_id in run_ids


def _checked_identity(entry: ReportIndexEntry, root: Path) -> dict[str, object]:
    report = (
        {"identity": entry.identity_snapshot}
        if entry.identity_snapshot is not None
        and entry.schema_version in {"pipeline_run_report_v1", "pipeline_run_report_v2"}
        else load_pipeline_run_report_payload(
            run_id=entry.run_id, pipeline_name=entry.owner, root=root
        )
    )
    if report is None:
        raise ValueError("Persisted selector report is unreadable or unsupported")
    identity = report.get("identity")
    if not isinstance(identity, dict):
        raise ValueError("Persisted selector report has no identity")
    if (
        identity.get("run_id") != entry.run_id
        or identity.get("pipeline_name") != entry.owner
    ):
        raise ValueError("Persisted selector report identity does not match its path")
    return identity


def _identity_matches_scopes(
    identity: dict[str, object], scopes: dict[str, tuple[str, ...]]
) -> bool:
    return not any(
        allowed and identity.get(_FIELDS[name]) not in allowed
        for name, values in scopes.items()
        if (allowed := _allowed_scope(values))
    )


def _option_label(
    dimension: str,
    identity: dict[str, object],
    entry: ReportIndexEntry,
    value: str,
    timezone: str = "UTC",
) -> str:
    if dimension != "run_id":
        return value
    raw = identity.get("started_at")
    try:
        moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        started = format_timestamp_label(moment, timezone)
    except (ValueError, TypeError):
        started = "UNKNOWN"
    return f"{started} · {entry.owner} · {identity.get('status', 'unknown')} · {value}"


def supplement_report_options(
    payload: dict[str, object],
    *,
    dimension: str,
    response_shape: str,
    scopes: dict[str, tuple[str, ...]],
    root: Path | None = None,
    timezone: str = "UTC",
    entries: list[ReportIndexEntry] | None = None,
) -> dict[str, object]:
    """Append genuine report identities; empty/error responses are never fabricated."""
    if dimension not in _FIELDS:
        return payload
    root = configured_report_root(root=root)
    if entries is None:
        entries = load_report_selector_entries(scopes, root=root)
    raw_items = payload.get("items", [])
    items = list(raw_items) if isinstance(raw_items, list) else []
    seen = {item.get("value") if isinstance(item, dict) else item for item in items}
    for entry in sorted(entries, key=lambda item: item.started_at or "", reverse=True):
        if not _entry_matches_catalog(entry, scopes):
            continue
        # Existing manifest-backed values already have their own evidence. Only
        # a newly contributed option needs the full report identity check.
        known_value = entry.owner if dimension == "pipeline" else entry.run_id
        if dimension in {"pipeline", "run_id"} and known_value in seen:
            continue
        identity = _checked_identity(entry, root)
        if not _identity_matches_scopes(identity, scopes):
            continue
        value = identity.get(_FIELDS[dimension])
        if not isinstance(value, str) or not value or value in seen:
            continue
        seen.add(value)
        label = _option_label(dimension, identity, entry, value, timezone)
        items.append(
            {"text": label, "value": value} if response_shape == "options" else value
        )
    return {**payload, "items": items}


def load_report_selector_entries(
    scopes: dict[str, tuple[str, ...]], *, root: Path | None = None
) -> list[ReportIndexEntry]:
    """Read only selected owners while preserving the complete historical catalog."""
    root = configured_report_root(root=root)
    pipelines = _allowed_scope(scopes.get("pipeline", ()))
    owners: list[str | None] = sorted(pipelines)
    if not pipelines:
        store = create_run_report_store()
        base = root / "pipeline"
        if not store.is_dir(str(base)):
            return []
        owners = [
            Path(location).name
            for location in store.iterdir(str(base))
            if store.is_dir(location)
        ]
        # Preserve legacy enumeration semantics for names that a selected-owner
        # lookup would normalize. Never silently omit unusual historical paths.
        if any(not re.fullmatch(r"[A-Za-z0-9_-]+", owner or "") for owner in owners):
            owners = [None]

    def read_owner(pipeline: str | None) -> list[ReportIndexEntry]:
        return list_pipeline_reports(
            pipeline_name=pipeline,
            root=root,
            limit=None,
            store=create_run_report_store(),
            include_markdown=False,
        )

    if not owners:
        return []
    if len(owners) == 1:
        return read_owner(owners[0])
    # Each worker owns its store. executor.map preserves owner order and raises
    # read failures rather than returning an incomplete successful catalog.
    with ThreadPoolExecutor(max_workers=_CATALOG_READ_WORKERS) as executor:
        entries = [
            entry for batch in executor.map(read_owner, owners) for entry in batch
        ]
    if not pipelines:
        entries.sort(key=lambda entry: entry.mtime, reverse=True)
    return entries
