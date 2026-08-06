# basedpyright residual burn-down (shrink-only product surface).
"""Filesystem writers for pipeline/workflow run reports."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from bioetl.application.services.run_reports.markdown import (
    render_pipeline_run_report_markdown,
    render_workflow_run_report_markdown,
)
from bioetl.application.services.run_reports.paths import (
    DEFAULT_REPORT_ROOT,
    REPORT_ROOT_MARKER_NAME,
    REPORT_ROOT_MARKER_TOKEN,
    inspect_report_root_marker,
    report_root_marker_is_healthy,
    report_root_marker_path,
    resolve_report_root,
)
from bioetl.domain.run_reports.models import PipelineRunReport, WorkflowRunReport

# Re-export path helpers so existing imports from writer keep working.
__all__ = (
    "DEFAULT_REPORT_ROOT",
    "REPORT_ROOT_MARKER_NAME",
    "REPORT_ROOT_MARKER_TOKEN",
    "RunReportWriteResult",
    "inspect_report_root_marker",
    "report_root_marker_is_healthy",
    "report_root_marker_path",
    "resolve_pipeline_report_dir",
    "resolve_report_root",
    "resolve_workflow_report_dir",
    "set_report_write_test_mode",
    "write_json",
    "write_pipeline_run_report",
    "write_workflow_run_report",
)

# Application must not read process env maps or import infrastructure Settings.
# Tests and composition can inject an explicit override; under pytest the
# runtime is treated as test mode so Windows cloud-synced worktrees do not
# stall on fsync during incidental report writes.
_test_mode_override: bool | None = None


@dataclass(frozen=True, slots=True)
class RunReportWriteResult:
    """Paths written for one report."""

    json_path: Path
    markdown_path: Path
    latest_path: Path | None = None


def set_report_write_test_mode(enabled: bool | None) -> None:
    """Override test-mode detection for report durability policy."""
    global _test_mode_override
    _test_mode_override = enabled


def _is_report_write_test_mode() -> bool:
    if _test_mode_override is not None:
        return _test_mode_override
    # Avoid process env maps: detect pytest runtime without Settings.
    import sys

    return "pytest" in sys.modules


def _safe_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
    return cleaned[:120] or "unknown"


def resolve_pipeline_report_dir(
    *,
    pipeline_name: str,
    run_id: str,
    root: Path | None = None,
) -> Path:
    base = resolve_report_root(root=root)
    return base / "pipeline" / _safe_segment(pipeline_name) / _safe_segment(run_id)


def resolve_workflow_report_dir(
    *,
    workflow_name: str,
    workflow_run_id: str,
    root: Path | None = None,
) -> Path:
    base = resolve_report_root(root=root)
    return (
        base
        / "workflow"
        / _safe_segment(workflow_name)
        / _safe_segment(workflow_run_id or "unknown")
    )


def _should_fsync_report_writes(*, os_name: str | None = None) -> bool:
    """Keep durable flushes unless Windows test runs explicitly relax them.

    Mirrors control-plane durability policy without importing infrastructure
    (application layer must stay free of infrastructure imports). Cloud-synced
    Windows worktrees (Google Drive / OneDrive) can stall on ``os.fsync`` long
    enough to trip the default 60s pytest-timeout while unit tests write
    incidental pipeline run reports.
    """
    current_os_name = os.name if os_name is None else os_name
    if current_os_name != "nt":
        return True
    return not _is_report_write_test_mode()


def _flush_report_file_descriptor(file_descriptor: int) -> None:
    """Flush one report file descriptor when durable writes are required."""
    if not _should_fsync_report_writes():
        return
    os.fsync(file_descriptor)


def _atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace one UTF-8 text artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            _flush_report_file_descriptor(stream.fileno())
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def write_json(path: Path, payload: Mapping[str, object]) -> None:
    """Write deterministic JSON through an atomic same-directory replacement."""
    _atomic_write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )


def _with_self_artifacts(
    artifacts: tuple[dict[str, Any], ...],  # Any: artifact payload
    *,
    json_path: Path,
    markdown_path: Path,
) -> tuple[dict[str, Any], ...]:  # Any: dynamic artifact payload
    kinds = {str(item.get("kind")) for item in artifacts}
    items = list(artifacts)
    if (
        "pipeline_run_report_json" not in kinds
        and "workflow_run_report_json" not in kinds
    ):
        kind = (
            "workflow_run_report_json"
            if json_path.name.startswith("workflow")
            else "pipeline_run_report_json"
        )
        items.append({"kind": kind, "ref": str(json_path.as_posix())})
    if "pipeline_run_report_md" not in kinds and "workflow_run_report_md" not in kinds:
        kind = (
            "workflow_run_report_md"
            if markdown_path.name.startswith("workflow")
            else "pipeline_run_report_md"
        )
        items.append({"kind": kind, "ref": str(markdown_path.as_posix())})
    return tuple(items)


def _write_latest_pointer(
    *,
    owner_dir: Path,
    payload: dict[str, Any],  # Any: latest pointer payload
) -> Path:
    latest_path = owner_dir / "_latest.json"
    write_json(latest_path, payload)
    return latest_path


def write_pipeline_run_report(
    report: PipelineRunReport,
    *,
    root: Path | None = None,
    directory: Path | None = None,
) -> RunReportWriteResult:
    """Write JSON + markdown pipeline run report artifacts and `_latest` pointer."""
    identity = report.identity
    out_dir = directory or resolve_pipeline_report_dir(
        pipeline_name=str(identity.get("pipeline_name", "pipeline")),
        run_id=str(identity.get("run_id", "run")),
        root=root,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "pipeline-run-report.json"
    md_path = out_dir / "pipeline-run-report.md"
    enriched = replace(
        report,
        artifacts=_with_self_artifacts(
            report.artifacts,
            json_path=json_path,
            markdown_path=md_path,
        ),
    )
    write_json(json_path, enriched.to_dict())
    _atomic_write_text(
        md_path,
        render_pipeline_run_report_markdown(enriched),
    )
    latest_path = _write_latest_pointer(
        owner_dir=out_dir.parent,
        payload={
            "kind": "pipeline_run_report",
            "pipeline_name": identity.get("pipeline_name"),
            "run_id": identity.get("run_id"),
            "status": identity.get("status"),
            "completed_at": identity.get("completed_at"),
            "json_path": str(json_path.as_posix()),
            "markdown_path": str(md_path.as_posix()),
        },
    )
    return RunReportWriteResult(
        json_path=json_path,
        markdown_path=md_path,
        latest_path=latest_path,
    )


def write_workflow_run_report(
    report: WorkflowRunReport,
    *,
    root: Path | None = None,
    directory: Path | None = None,
) -> RunReportWriteResult:
    """Write JSON + markdown workflow run report artifacts and `_latest` pointer."""
    identity = report.identity
    out_dir = directory or resolve_workflow_report_dir(
        workflow_name=str(identity.get("workflow_name", "workflow")),
        workflow_run_id=str(identity.get("workflow_run_id") or "unknown"),
        root=root,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "workflow-run-report.json"
    md_path = out_dir / "workflow-run-report.md"
    write_json(json_path, report.to_dict())
    _atomic_write_text(md_path, render_workflow_run_report_markdown(report))
    latest_path = _write_latest_pointer(
        owner_dir=out_dir.parent,
        payload={
            "kind": "workflow_run_report",
            "workflow_name": identity.get("workflow_name"),
            "workflow_run_id": identity.get("workflow_run_id"),
            "status": identity.get("status"),
            "completed_at": identity.get("completed_at"),
            "json_path": str(json_path.as_posix()),
            "markdown_path": str(md_path.as_posix()),
        },
    )
    return RunReportWriteResult(
        json_path=json_path,
        markdown_path=md_path,
        latest_path=latest_path,
    )
