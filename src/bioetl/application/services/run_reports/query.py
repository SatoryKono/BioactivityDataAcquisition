"""Read/list/diff/prune helpers for persisted run reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bioetl.application.services.run_reports.writer import (
    DEFAULT_REPORT_ROOT,
    _safe_segment,
)


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


def _root(root: Path | None) -> Path:
    return root or DEFAULT_REPORT_ROOT


def load_latest_pointer(
    *,
    kind: str,
    owner: str,
    root: Path | None = None,
) -> dict[str, Any] | None:  # Any: latest pointer
    base = _root(root) / kind / _safe_segment(owner) / "_latest.json"
    if not base.is_file():
        return None
    payload = json.loads(base.read_text(encoding="utf-8"))
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
        pointer = load_latest_pointer(kind="pipeline", owner=pipeline_name, root=base)
        if pointer is None:
            return None
        path = Path(str(pointer.get("json_path") or ""))
        if not path.is_file():
            # fallback relative to repo
            path = Path(str(pointer.get("json_path") or ""))
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    path = (
        base
        / "pipeline"
        / _safe_segment(pipeline_name)
        / _safe_segment(run_id)
        / "pipeline-run-report.json"
    )
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def load_workflow_report(
    *,
    workflow_name: str,
    workflow_run_id: str | None = None,
    latest: bool = False,
    root: Path | None = None,
) -> dict[str, Any] | None:  # Any: report payload
    base = _root(root)
    if latest or workflow_run_id is None:
        pointer = load_latest_pointer(kind="workflow", owner=workflow_name, root=base)
        if pointer is None:
            return None
        path = Path(str(pointer.get("json_path") or ""))
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    path = (
        base
        / "workflow"
        / _safe_segment(workflow_name)
        / _safe_segment(workflow_run_id)
        / "workflow-run-report.json"
    )
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def list_pipeline_reports(
    *,
    pipeline_name: str | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> list[ReportIndexEntry]:
    base = _root(root) / "pipeline"
    if not base.is_dir():
        return []
    owners = (
        [base / _safe_segment(pipeline_name)]
        if pipeline_name
        else [path for path in base.iterdir() if path.is_dir()]
    )
    entries: list[ReportIndexEntry] = []
    for owner_dir in owners:
        if not owner_dir.is_dir():
            continue
        for run_dir in owner_dir.iterdir():
            if not run_dir.is_dir() or run_dir.name.startswith("."):
                continue
            json_path = run_dir / "pipeline-run-report.json"
            if not json_path.is_file():
                continue
            status, completed_at = _read_identity_meta(json_path)
            md_path = run_dir / "pipeline-run-report.md"
            entries.append(
                ReportIndexEntry(
                    kind="pipeline",
                    owner=owner_dir.name,
                    run_id=run_dir.name,
                    json_path=json_path,
                    markdown_path=md_path if md_path.is_file() else None,
                    status=status,
                    completed_at=completed_at,
                    mtime=json_path.stat().st_mtime,
                )
            )
    entries.sort(key=lambda item: item.mtime, reverse=True)
    return entries[: max(0, limit)]


def list_workflow_reports(
    *,
    workflow_name: str | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> list[ReportIndexEntry]:
    base = _root(root) / "workflow"
    if not base.is_dir():
        return []
    owners = (
        [base / _safe_segment(workflow_name)]
        if workflow_name
        else [path for path in base.iterdir() if path.is_dir()]
    )
    entries: list[ReportIndexEntry] = []
    for owner_dir in owners:
        if not owner_dir.is_dir():
            continue
        for run_dir in owner_dir.iterdir():
            if not run_dir.is_dir() or run_dir.name.startswith("."):
                continue
            json_path = run_dir / "workflow-run-report.json"
            if not json_path.is_file():
                continue
            status, completed_at = _read_identity_meta(json_path)
            md_path = run_dir / "workflow-run-report.md"
            entries.append(
                ReportIndexEntry(
                    kind="workflow",
                    owner=owner_dir.name,
                    run_id=run_dir.name,
                    json_path=json_path,
                    markdown_path=md_path if md_path.is_file() else None,
                    status=status,
                    completed_at=completed_at,
                    mtime=json_path.stat().st_mtime,
                )
            )
    entries.sort(key=lambda item: item.mtime, reverse=True)
    return entries[: max(0, limit)]


def diff_pipeline_reports(
    left: MappingLike,
    right: MappingLike,
) -> dict[str, Any]:  # Any: diff payload
    """Compute funnel and reason deltas between two pipeline report payloads."""
    left_payload = _as_mapping(left)
    right_payload = _as_mapping(right)
    left_funnel = {
        str(row.get("stage_id")): row
        for row in left_payload.get("funnel") or []
        if isinstance(row, dict)
    }
    right_funnel = {
        str(row.get("stage_id")): row
        for row in right_payload.get("funnel") or []
        if isinstance(row, dict)
    }
    stages = sorted(set(left_funnel) | set(right_funnel))
    funnel_delta = []
    for stage in stages:
        lrow = left_funnel.get(stage, {})
        rrow = right_funnel.get(stage, {})
        funnel_delta.append(
            {
                "stage_id": stage,
                "records_in_delta": _int(rrow.get("records_in"))
                - _int(lrow.get("records_in")),
                "records_out_delta": _int(rrow.get("records_out"))
                - _int(lrow.get("records_out")),
                "removed_total_delta": _int(rrow.get("removed_total"))
                - _int(lrow.get("removed_total")),
            }
        )
    left_reasons = {
        str(item.get("reason_code")): _int(item.get("count"))
        for item in left_payload.get("reasons_top_n") or []
        if isinstance(item, dict)
    }
    right_reasons = {
        str(item.get("reason_code")): _int(item.get("count"))
        for item in right_payload.get("reasons_top_n") or []
        if isinstance(item, dict)
    }
    reason_codes = sorted(set(left_reasons) | set(right_reasons))
    reasons_delta = [
        {
            "reason_code": code,
            "count_delta": right_reasons.get(code, 0) - left_reasons.get(code, 0),
        }
        for code in reason_codes
    ]
    return {
        "left_run_id": (left_payload.get("identity") or {}).get("run_id"),
        "right_run_id": (right_payload.get("identity") or {}).get("run_id"),
        "funnel_delta": funnel_delta,
        "reasons_delta": reasons_delta,
    }


def prune_reports(
    *,
    kind: str,
    owner: str | None = None,
    max_count: int | None = None,
    max_age_days: int | None = None,
    root: Path | None = None,
    dry_run: bool = True,
) -> list[str]:
    """Delete old report directories. Returns removed paths (or candidates if dry_run)."""
    if kind not in {"pipeline", "workflow"}:
        raise ValueError("kind must be 'pipeline' or 'workflow'")
    if max_count is None and max_age_days is None:
        raise ValueError("provide max_count and/or max_age_days")
    entries = (
        list_pipeline_reports(pipeline_name=owner, limit=10_000, root=root)
        if kind == "pipeline"
        else list_workflow_reports(workflow_name=owner, limit=10_000, root=root)
    )
    now = datetime.now(tz=UTC).timestamp()
    victims: list[ReportIndexEntry] = []
    if max_age_days is not None:
        cutoff = now - (max_age_days * 86400)
        victims.extend(item for item in entries if item.mtime < cutoff)
    if max_count is not None and len(entries) > max_count:
        victims.extend(entries[max_count:])
    # unique by path
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


def _read_identity_meta(path: Path) -> tuple[str | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    identity = payload.get("identity") if isinstance(payload, dict) else None
    if not isinstance(identity, dict):
        return None, None
    status = identity.get("status")
    completed = identity.get("completed_at")
    return (
        str(status) if status is not None else None,
        str(completed) if completed is not None else None,
    )


def _int(value: object) -> int:
    try:
        return 0 if value is None else int(value)
    except (TypeError, ValueError):
        return 0


MappingLike = dict[str, Any] | Any  # Any: decoded external JSON payload


def _as_mapping(
    value: MappingLike,  # Any: decoded external JSON payload
) -> dict[str, Any]:  # Any: validated dynamic report mapping
    if isinstance(value, dict):
        return value
    raise TypeError("report payload must be a mapping")


def _rm_tree(path: Path) -> None:
    if path.is_file():
        path.unlink(missing_ok=True)
        return
    for child in path.iterdir():
        _rm_tree(child)
    path.rmdir()
