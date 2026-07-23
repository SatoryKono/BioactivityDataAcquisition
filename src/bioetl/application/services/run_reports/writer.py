"""Filesystem writers for pipeline/workflow run reports."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bioetl.application.services.run_reports.markdown import (
    render_pipeline_run_report_markdown,
    render_workflow_run_report_markdown,
)
from bioetl.domain.run_reports.models import PipelineRunReport, WorkflowRunReport

DEFAULT_REPORT_ROOT = Path("reports") / "run-reports"


@dataclass(frozen=True, slots=True)
class RunReportWriteResult:
    """Paths written for one report."""

    json_path: Path
    markdown_path: Path


def _safe_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
    return cleaned[:120] or "unknown"


def resolve_pipeline_report_dir(
    *,
    pipeline_name: str,
    run_id: str,
    root: Path | None = None,
) -> Path:
    base = root or DEFAULT_REPORT_ROOT
    return base / "pipeline" / _safe_segment(pipeline_name) / _safe_segment(run_id)


def resolve_workflow_report_dir(
    *,
    workflow_name: str,
    workflow_run_id: str,
    root: Path | None = None,
) -> Path:
    base = root or DEFAULT_REPORT_ROOT
    return (
        base
        / "workflow"
        / _safe_segment(workflow_name)
        / _safe_segment(workflow_run_id or "unknown")
    )


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
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def write_json(path: Path, payload: dict[str, Any]) -> None:  # Any: report/json payload shape is dynamic
    """Write deterministic JSON through an atomic same-directory replacement."""
    _atomic_write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )


def write_pipeline_run_report(
    report: PipelineRunReport,
    *,
    root: Path | None = None,
    directory: Path | None = None,
) -> RunReportWriteResult:
    """Write JSON + markdown pipeline run report artifacts."""
    identity = report.identity
    out_dir = directory or resolve_pipeline_report_dir(
        pipeline_name=str(identity.get("pipeline_name", "pipeline")),
        run_id=str(identity.get("run_id", "run")),
        root=root,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "pipeline-run-report.json"
    md_path = out_dir / "pipeline-run-report.md"
    write_json(json_path, report.to_dict())
    _atomic_write_text(md_path, render_pipeline_run_report_markdown(report))
    return RunReportWriteResult(json_path=json_path, markdown_path=md_path)


def write_workflow_run_report(
    report: WorkflowRunReport,
    *,
    root: Path | None = None,
    directory: Path | None = None,
) -> RunReportWriteResult:
    """Write JSON + markdown workflow run report artifacts."""
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
    return RunReportWriteResult(json_path=json_path, markdown_path=md_path)
