"""Read/list/diff/prune helpers for persisted run reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bioetl.application.services.run_reports._report_diff_support import (
    diff_pipeline_reports as diff_pipeline_reports,
)
from bioetl.application.services.run_reports.paths import (
    read_identity_preview,
    resolve_report_root,
)
from bioetl.application.services.run_reports.writer import _safe_segment
from bioetl.domain.ports import RunReportStorePort


@dataclass(frozen=True, slots=True)
class ReportIndexEntry:
    """One discovered run report."""

    kind: str
    owner: str
    run_id: str
    json_path: Path
    markdown_path: Path | None
    status: str | None
    started_at: str | None
    completed_at: str | None
    mtime: float
    workflow_id: str | None = None
    workflow_run_id: str | None = None
    run_type: str | None = None


def _root(root: Path | None) -> Path:
    return resolve_report_root(root=root)


def load_latest_pointer(
    *, kind: str, owner: str, root: Path | None = None, store: RunReportStorePort
) -> dict[str, Any] | None:  # Any: latest pointer
    base = _root(root) / kind / _safe_segment(owner) / "_latest.json"
    if not store.is_file(str(base)):
        return None
    try:
        payload = json.loads(store.read_text(str(base)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def load_pipeline_report(
    *,
    pipeline_name: str,
    run_id: str | None = None,
    latest: bool = False,
    root: Path | None = None,
    store: RunReportStorePort,
) -> dict[str, Any] | None:  # Any: report payload
    base = _root(root)
    if latest or run_id is None:
        return _load_latest_report(
            kind="pipeline", owner=pipeline_name, root=base, store=store
        )
    path = (
        base
        / "pipeline"
        / _safe_segment(pipeline_name)
        / _safe_segment(run_id)
        / "pipeline-run-report.json"
    )
    return _load_json_dict(path, store=store)


def load_workflow_report(
    *,
    workflow_name: str,
    workflow_run_id: str | None = None,
    latest: bool = False,
    root: Path | None = None,
    store: RunReportStorePort,
) -> dict[str, Any] | None:  # Any: report payload
    base = _root(root)
    if latest or workflow_run_id is None:
        return _load_latest_report(
            kind="workflow", owner=workflow_name, root=base, store=store
        )
    path = (
        base
        / "workflow"
        / _safe_segment(workflow_name)
        / _safe_segment(workflow_run_id)
        / "workflow-run-report.json"
    )
    return _load_json_dict(path, store=store)


def _load_latest_report(
    *, kind: str, owner: str, root: Path, store: RunReportStorePort
) -> dict[str, Any] | None:  # Any: decoded report payload
    pointer = load_latest_pointer(kind=kind, owner=owner, root=root, store=store)
    if pointer is None:
        return None
    return _load_json_dict(Path(str(pointer.get("json_path") or "")), store=store)


def _load_json_dict(
    path: Path, *, store: RunReportStorePort
) -> dict[str, Any] | None:  # Any: decoded JSON object
    if not store.is_file(str(path)):
        return None
    try:
        payload = json.loads(store.read_text(str(path)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def list_pipeline_reports(
    *,
    pipeline_name: str | None = None,
    limit: int | None = 20,
    root: Path | None = None,
    store: RunReportStorePort,
) -> list[ReportIndexEntry]:
    return _list_reports(
        kind="pipeline", owner=pipeline_name, limit=limit, root=root, store=store
    )


def list_workflow_reports(
    *,
    workflow_name: str | None = None,
    limit: int = 20,
    root: Path | None = None,
    store: RunReportStorePort,
) -> list[ReportIndexEntry]:
    return _list_reports(
        kind="workflow", owner=workflow_name, limit=limit, root=root, store=store
    )


def _list_reports(
    *,
    kind: str,
    owner: str | None,
    limit: int | None,
    root: Path | None,
    store: RunReportStorePort,
) -> list[ReportIndexEntry]:
    """List newest reports by mtime first; hydrate meta only for top ``limit``."""
    base = _root(root) / kind
    if not store.is_dir(str(base)):
        return []
    candidates = _collect_report_candidates(
        base=base, kind=kind, owner=owner, store=store
    )
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [
        _build_report_index_entry(
            kind=kind,
            mtime=mtime,
            owner_name=owner_name,
            run_dir=run_dir,
            json_path=json_path,
            store=store,
        )
        for mtime, owner_name, run_dir, json_path in _limit_report_candidates(
            candidates,
            limit,
        )
    ]


def _limit_report_candidates(
    candidates: list[tuple[float, str, Path, Path]],
    limit: int | None,
) -> list[tuple[float, str, Path, Path]]:
    """Return an optional ranked prefix without imposing a retention cap."""
    if limit is None:
        return candidates
    return candidates[: max(0, limit)]


def _collect_report_candidates(
    *, base: Path, kind: str, owner: str | None, store: RunReportStorePort
) -> list[tuple[float, str, Path, Path]]:
    """Collect sortable report paths without hydrating report payloads."""
    report_name = f"{kind}-run-report.json"
    candidates: list[tuple[float, str, Path, Path]] = []
    for owner_dir in _owner_directories(base, owner, store=store):
        if not store.is_dir(str(owner_dir)):
            continue
        for run_dir in (Path(location) for location in store.iterdir(str(owner_dir))):
            if not store.is_dir(str(run_dir)) or run_dir.name.startswith("."):
                continue
            json_path = run_dir / report_name
            if not store.is_file(str(json_path)):
                continue
            try:
                mtime = store.mtime(str(json_path))
            except OSError:
                continue
            candidates.append((mtime, owner_dir.name, run_dir, json_path))
    return candidates


def _build_report_index_entry(
    *,
    kind: str,
    mtime: float,
    owner_name: str,
    run_dir: Path,
    json_path: Path,
    store: RunReportStorePort,
) -> ReportIndexEntry:
    """Hydrate one ranked report candidate."""
    meta = read_identity_preview(json_path, store=store)
    md_path = run_dir / f"{kind}-run-report.md"
    return ReportIndexEntry(
        kind=kind,
        owner=owner_name,
        run_id=run_dir.name,
        json_path=json_path,
        markdown_path=md_path if store.is_file(str(md_path)) else None,
        status=meta.status,
        started_at=meta.started_at,
        completed_at=meta.completed_at,
        mtime=mtime,
        workflow_id=meta.workflow_id if kind == "pipeline" else None,
        workflow_run_id=meta.workflow_run_id if kind == "pipeline" else None,
        run_type=meta.run_type if kind == "pipeline" else None,
    )


def _owner_directories(
    base: Path, owner: str | None, *, store: RunReportStorePort
) -> list[Path]:
    if owner:
        return [base / _safe_segment(owner)]
    return [
        path
        for path in (Path(location) for location in store.iterdir(str(base)))
        if store.is_dir(str(path))
    ]


def find_pipeline_report_owner_names(
    *, base: Path, run_id: str, store: RunReportStorePort
) -> list[str]:
    """Return sorted owner names holding ``run_id``'s pipeline report.

    Discovery goes through the storage port (``iterdir``/``is_file``) so
    driving adapters never traverse the filesystem directly (REQ-ARCH-001).
    """
    if not store.is_dir(str(base)):
        return []
    safe_run_id = _safe_segment(run_id)
    owners = []
    for owner_dir in _owner_directories(base, None, store=store):
        candidate = owner_dir / safe_run_id / "pipeline-run-report.json"
        if store.is_file(str(candidate)):
            owners.append(owner_dir.name)
    return sorted(owners)


def prune_reports(
    *,
    kind: str,
    owner: str | None = None,
    max_count: int | None = None,
    max_age_days: int | None = None,
    now: datetime | None = None,
    root: Path | None = None,
    dry_run: bool = True,
    store: RunReportStorePort,
) -> list[str]:
    """Delete old report directories. Returns removed paths (or candidates if dry_run)."""
    _validate_prune_options(kind, max_count, max_age_days, now)
    entries = _reports_for_prune(kind, owner, root, store=store)
    victims = _prune_candidates(entries, max_count, max_age_days, now)
    return _remove_report_directories(victims, dry_run=dry_run, store=store)


def _validate_prune_options(
    kind: str,
    max_count: int | None,
    max_age_days: int | None,
    now: datetime | None,
) -> None:
    if kind not in {"pipeline", "workflow"}:
        raise ValueError("kind must be 'pipeline' or 'workflow'")
    if max_count is None and max_age_days is None:
        raise ValueError("provide max_count and/or max_age_days")
    if max_age_days is not None and now is None:
        raise ValueError("now is required when max_age_days is provided")


def _reports_for_prune(
    kind: str, owner: str | None, root: Path | None, *, store: RunReportStorePort
) -> list[ReportIndexEntry]:
    return _list_reports(kind=kind, owner=owner, limit=None, root=root, store=store)


def _prune_candidates(
    entries: list[ReportIndexEntry],
    max_count: int | None,
    max_age_days: int | None,
    now: datetime | None,
) -> list[ReportIndexEntry]:
    """Select victims from entries sorted by modification time descending."""
    victims: list[ReportIndexEntry] = []
    if max_age_days is not None and now is not None:
        cutoff = now.astimezone(UTC).timestamp() - (max_age_days * 86400)
        victims.extend(item for item in entries if item.mtime < cutoff)
    if max_count is not None:
        victims.extend(entries[max_count:])
    return victims


def _remove_report_directories(
    victims: list[ReportIndexEntry], *, dry_run: bool, store: RunReportStorePort
) -> list[str]:
    seen: set[Path] = set()
    removed: list[str] = []
    for item in victims:
        directory = item.json_path.parent
        if directory in seen:
            continue
        seen.add(directory)
        removed.append(str(directory.as_posix()))
        if not dry_run:
            store.remove_tree(str(directory), root=str(directory.parent.parent.parent))
    return removed
