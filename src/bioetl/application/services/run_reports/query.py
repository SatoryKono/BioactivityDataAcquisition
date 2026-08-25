"""Read/list/diff/prune helpers for persisted run reports."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bioetl.application.services.run_reports.paths import resolve_report_root
from bioetl.application.services.run_reports.writer import _safe_segment


@dataclass(frozen=True, slots=True)
class ReportIndexEntry:
    """One discovered run report."""

    kind: str
    owner: str
    run_id: str
    json_path: Path
    markdown_path: Path | None
    status: str | None
    completed_at: str | None
    mtime: float
    workflow_id: str | None = None


def _root(root: Path | None) -> Path:
    return resolve_report_root(root=root)


def load_latest_pointer(
    *,
    kind: str,
    owner: str,
    root: Path | None = None,
) -> dict[str, Any] | None:  # Any: latest pointer
    base = _root(root) / kind / _safe_segment(owner) / "_latest.json"
    if not base.is_file():
        return None
    try:
        payload = json.loads(base.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def load_pipeline_report(
    *,
    pipeline_name: str,
    run_id: str | None = None,
    latest: bool = False,
    root: Path | None = None,
) -> dict[str, Any] | None:  # Any: report payload
    base = _root(root)
    if latest or run_id is None:
        return _load_latest_report(kind="pipeline", owner=pipeline_name, root=base)
    path = (
        base
        / "pipeline"
        / _safe_segment(pipeline_name)
        / _safe_segment(run_id)
        / "pipeline-run-report.json"
    )
    return _load_json_dict(path)


def load_workflow_report(
    *,
    workflow_name: str,
    workflow_run_id: str | None = None,
    latest: bool = False,
    root: Path | None = None,
) -> dict[str, Any] | None:  # Any: report payload
    base = _root(root)
    if latest or workflow_run_id is None:
        return _load_latest_report(kind="workflow", owner=workflow_name, root=base)
    path = (
        base
        / "workflow"
        / _safe_segment(workflow_name)
        / _safe_segment(workflow_run_id)
        / "workflow-run-report.json"
    )
    return _load_json_dict(path)


def _load_latest_report(
    *,
    kind: str,
    owner: str,
    root: Path,
) -> dict[str, Any] | None:  # Any: decoded report payload
    pointer = load_latest_pointer(kind=kind, owner=owner, root=root)
    if pointer is None:
        return None
    return _load_json_dict(Path(str(pointer.get("json_path") or "")))


def _load_json_dict(path: Path) -> dict[str, Any] | None:  # Any: decoded JSON object
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def list_pipeline_reports(
    *,
    pipeline_name: str | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> list[ReportIndexEntry]:
    return _list_reports(kind="pipeline", owner=pipeline_name, limit=limit, root=root)


def list_workflow_reports(
    *,
    workflow_name: str | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> list[ReportIndexEntry]:
    return _list_reports(kind="workflow", owner=workflow_name, limit=limit, root=root)


def _list_reports(
    *,
    kind: str,
    owner: str | None,
    limit: int | None,
    root: Path | None,
) -> list[ReportIndexEntry]:
    """List newest reports by mtime first; hydrate meta only for top ``limit``."""
    base = _root(root) / kind
    if not base.is_dir():
        return []
    candidates = _collect_report_candidates(base=base, kind=kind, owner=owner)
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [
        _build_report_index_entry(
            kind=kind,
            mtime=mtime,
            owner_name=owner_name,
            run_dir=run_dir,
            json_path=json_path,
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
    *,
    base: Path,
    kind: str,
    owner: str | None,
) -> list[tuple[float, str, Path, Path]]:
    """Collect sortable report paths without hydrating report payloads."""
    report_name = f"{kind}-run-report.json"
    candidates: list[tuple[float, str, Path, Path]] = []
    for owner_dir in _owner_directories(base, owner):
        if not owner_dir.is_dir():
            continue
        for run_dir in owner_dir.iterdir():
            if not run_dir.is_dir() or run_dir.name.startswith("."):
                continue
            json_path = run_dir / report_name
            if not json_path.is_file():
                continue
            try:
                mtime = json_path.stat().st_mtime
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
) -> ReportIndexEntry:
    """Hydrate one ranked report candidate."""
    status, completed_at, workflow_id = _read_identity_meta(json_path)
    md_path = run_dir / f"{kind}-run-report.md"
    return ReportIndexEntry(
        kind=kind,
        owner=owner_name,
        run_id=run_dir.name,
        json_path=json_path,
        markdown_path=md_path if md_path.is_file() else None,
        status=status,
        completed_at=completed_at,
        mtime=mtime,
        workflow_id=workflow_id if kind == "pipeline" else None,
    )


def _owner_directories(base: Path, owner: str | None) -> list[Path]:
    if owner:
        return [base / _safe_segment(owner)]
    return [path for path in base.iterdir() if path.is_dir()]


def diff_pipeline_reports(left: MappingLike, right: MappingLike) -> ReportPayload:
    """Compute funnel and reason deltas between two pipeline report payloads."""
    left_payload = _as_mapping(left)
    right_payload = _as_mapping(right)
    return {
        "left_run_id": (left_payload.get("identity") or {}).get("run_id"),
        "right_run_id": (right_payload.get("identity") or {}).get("run_id"),
        "funnel_delta": _funnel_delta(left_payload, right_payload),
        "reasons_delta": _reasons_delta(left_payload, right_payload),
    }


def _funnel_rows(payload: ReportPayload) -> dict[str, ReportPayload]:
    return {
        str(row.get("stage_id")): row
        for row in payload.get("funnel") or []
        if isinstance(row, dict)
    }


def _funnel_delta(
    left: dict[str, Any],  # Any: decoded report payload
    right: dict[str, Any],  # Any: decoded report payload
) -> list[dict[str, Any]]:  # Any: dynamic funnel delta rows
    left_rows = _funnel_rows(left)
    right_rows = _funnel_rows(right)
    stages = sorted(set(left_rows) | set(right_rows))
    return [
        _stage_delta(stage, left_rows.get(stage, {}), right_rows.get(stage, {}))
        for stage in stages
    ]


def _stage_delta(
    stage: str,
    left: dict[str, Any],  # Any: dynamic funnel row
    right: dict[str, Any],  # Any: dynamic funnel row
) -> dict[str, Any]:  # Any: dynamic stage delta payload
    return {
        "stage_id": stage,
        "records_in_delta": _int(right.get("records_in")) - _int(left.get("records_in")),
        "records_out_delta": _int(right.get("records_out")) - _int(left.get("records_out")),
        "removed_total_delta": _int(right.get("removed_total")) - _int(left.get("removed_total")),
    }


def _reason_counts(payload: ReportPayload) -> dict[str, int]:
    items = payload.get("reasons_top_n") or []
    return {str(i.get("reason_code")): _int(i.get("count")) for i in items if isinstance(i, dict)}


def _reasons_delta(
    left: dict[str, Any],  # Any: decoded report payload
    right: dict[str, Any],  # Any: decoded report payload
) -> list[dict[str, Any]]:  # Any: dynamic reason delta rows
    left_counts = _reason_counts(left)
    right_counts = _reason_counts(right)
    return [
        {
            "reason_code": code,
            "count_delta": right_counts.get(code, 0) - left_counts.get(code, 0),
        }
        for code in sorted(set(left_counts) | set(right_counts))
    ]


def prune_reports(
    *,
    kind: str,
    owner: str | None = None,
    max_count: int | None = None,
    max_age_days: int | None = None,
    now: datetime | None = None,
    root: Path | None = None,
    dry_run: bool = True,
) -> list[str]:
    """Delete old report directories. Returns removed paths (or candidates if dry_run)."""
    _validate_prune_options(kind, max_count, max_age_days, now)
    entries = _reports_for_prune(kind, owner, root)
    victims = _prune_candidates(entries, max_count, max_age_days, now)
    return _remove_report_directories(victims, dry_run=dry_run)


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
    kind: str,
    owner: str | None,
    root: Path | None,
) -> list[ReportIndexEntry]:
    return _list_reports(kind=kind, owner=owner, limit=None, root=root)


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
    victims: list[ReportIndexEntry],
    *,
    dry_run: bool,
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
            _rm_tree(directory)
    return removed


def _read_identity_meta(
    path: Path,
) -> tuple[str | None, str | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None, None
    identity = payload.get("identity") if isinstance(payload, dict) else None
    if not isinstance(identity, dict):
        return None, None, None
    status = identity.get("status")
    completed = identity.get("completed_at")
    workflow_raw = identity.get("workflow_id")
    workflow_id = str(workflow_raw).strip() if workflow_raw is not None else ""
    return (
        str(status) if status is not None else None,
        str(completed) if completed is not None else None,
        workflow_id or None,
    )


def _int(value: object) -> int:
    if value is None:
        return 0
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return 0


MappingLike = dict[str, Any] | Any  # Any: decoded external JSON payload
ReportPayload = dict[str, Any]  # Any: decoded report JSON payload


def _as_mapping(value: MappingLike) -> ReportPayload:
    if isinstance(value, dict):
        return value
    raise TypeError("report payload must be a mapping")


def _rm_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    shutil.rmtree(path)
