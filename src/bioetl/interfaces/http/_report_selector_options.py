"""Supplement selector catalogs with identity-checked persisted run reports."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from bioetl.application.services.run_reports.query import (
    ReportIndexEntry,
    list_pipeline_reports,
)
from bioetl.composition.observability_runtime import create_run_report_store
from bioetl.domain.ports import RunReportStorePort
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


def _maybe_report_option(
    *,
    entry: ReportIndexEntry,
    dimension: str,
    response_shape: str,
    scopes: dict[str, tuple[str, ...]],
    root: Path,
    timezone: str,
    seen: set[object],
) -> object | None:
    if not _entry_matches_catalog(entry, scopes):
        return None
    known_value = entry.owner if dimension == "pipeline" else entry.run_id
    if dimension in {"pipeline", "run_id"} and known_value in seen:
        return None
    identity = _checked_identity(entry, root)
    if not _identity_matches_scopes(identity, scopes):
        return None
    value = identity.get(_FIELDS[dimension])
    if not isinstance(value, str) or not value or value in seen:
        return None
    seen.add(value)
    label = _option_label(dimension, identity, entry, value, timezone)
    if response_shape == "options":
        return {"text": label, "value": value}
    return value


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
        option = _maybe_report_option(
            entry=entry,
            dimension=dimension,
            response_shape=response_shape,
            scopes=scopes,
            root=root,
            timezone=timezone,
            seen=seen,
        )
        if option is not None:
            items.append(option)
    return {**payload, "items": items}


def filtered_report_run_candidates(
    scopes: dict[str, tuple[str, ...]],
    *,
    root: Path | None = None,
    store: RunReportStorePort | None = None,
    entries: list[ReportIndexEntry] | None = None,
) -> tuple[tuple[str, datetime], ...]:
    """Return identity-checked ``(run_id, started_at)`` rows for A2 / selector sync.

    Uses the same scope + identity gates as ``supplement_report_options`` so
    report-only runs that appear in filter-options also participate in latest
    selection and empty-scope checks. Rows without a parseable ``started_at``
    are excluded here only — A2 ordering needs a timestamp — while explicit
    UUID lookup via ``verified_report_identity_for_run`` still resolves them.
    """
    return tuple(
        (run_id, started)
        for run_id, started, _identity in _iter_verified_report_identities(
            scopes, root=root, store=store, entries=entries
        )
        if started is not None
    )


def verified_report_identity_for_run(
    run_id: str,
    scopes: dict[str, tuple[str, ...]],
    *,
    root: Path | None = None,
    store: RunReportStorePort | None = None,
    entries: list[ReportIndexEntry] | None = None,
) -> dict[str, object] | None:
    """Return the verified report identity for one run_id in scope, if present.

    The requested ``run_id`` is injected into scopes **before** identity checks so
    unrelated corrupt reports in the same pipeline catalog cannot raise
    ``ValueError`` and block a good explicit UUID. Missing ``started_at`` does
    not drop the identity — filter-options labels already render ``UNKNOWN``.
    """
    narrowed = {**scopes, "run_id": (run_id,)}
    for candidate_id, _started, identity in _iter_verified_report_identities(
        narrowed, root=root, store=store, entries=entries
    ):
        if candidate_id == run_id:
            return identity
    return None


def _iter_verified_report_identities(
    scopes: dict[str, tuple[str, ...]],
    *,
    root: Path | None = None,
    store: RunReportStorePort | None = None,
    entries: list[ReportIndexEntry] | None = None,
) -> tuple[tuple[str, datetime | None, dict[str, object]], ...]:
    root = configured_report_root(root=root)
    if entries is None:
        entries = load_report_selector_entries(scopes, root=root, store=store)
    rows: list[tuple[str, datetime | None, dict[str, object]]] = []
    seen: set[str] = set()
    for entry in sorted(entries, key=lambda item: item.started_at or "", reverse=True):
        if not _entry_matches_catalog(entry, scopes):
            continue
        # Propagate identity/path mismatches: callers (A2 / selected-run-status)
        # map ValueError to QUERY ERROR instead of treating a corrupt catalog as empty.
        identity = _checked_identity(entry, root)
        if not _identity_matches_scopes(identity, scopes):
            continue
        run_id = identity.get("run_id")
        if not isinstance(run_id, str) or not run_id or run_id in seen:
            continue
        # Keep verified rows even when started_at is absent; A2 candidate
        # catalog applies the timestamp gate separately.
        started = _identity_started_at(identity, entry)
        seen.add(run_id)
        rows.append((run_id, started, identity))
    return tuple(rows)


def _identity_started_at(
    identity: dict[str, object], entry: ReportIndexEntry
) -> datetime | None:
    raw = identity.get("started_at") or entry.started_at
    if raw is None:
        return None
    try:
        moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment


def load_report_selector_entries(
    scopes: dict[str, tuple[str, ...]],
    *,
    root: Path | None = None,
    store: RunReportStorePort | None = None,
) -> list[ReportIndexEntry]:
    """Read only selected owners while preserving the complete historical catalog."""
    root = configured_report_root(root=root)
    # Direct callers retain a bounded fallback; server readers inject their port.
    store = store if store is not None else create_run_report_store()
    pipelines = _allowed_scope(scopes.get("pipeline", ()))
    owners = _catalog_owners(root, store, pipelines)

    def read_owner(pipeline: str | None) -> list[ReportIndexEntry]:
        return list_pipeline_reports(
            pipeline_name=pipeline,
            root=root,
            limit=None,
            store=store,
            include_markdown=False,
        )

    if not owners:
        return []
    if len(owners) == 1:
        return read_owner(owners[0])
    # The filesystem adapter has no mutable per-reader state. Workers share the
    # host's read port; executor.map preserves owner order and raises
    # read failures rather than returning an incomplete successful catalog.
    with ThreadPoolExecutor(max_workers=_CATALOG_READ_WORKERS) as executor:
        entries = [
            entry for batch in executor.map(read_owner, owners) for entry in batch
        ]
    if not pipelines:
        entries.sort(key=lambda entry: entry.mtime, reverse=True)
    return entries


def _catalog_owners(
    root: Path, store: RunReportStorePort, pipelines: set[str]
) -> list[str | None]:
    """Preserve unusual historical owner names through legacy enumeration."""
    if pipelines:
        selected: list[str | None] = []
        selected.extend(sorted(pipelines))
        return selected
    base = root / "pipeline"
    if not store.is_dir(str(base)):
        return []
    owners = [
        Path(location).name
        for location in store.iterdir(str(base))
        if store.is_dir(location)
    ]
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", owner or "") for owner in owners):
        return [None]
    return list(owners)
