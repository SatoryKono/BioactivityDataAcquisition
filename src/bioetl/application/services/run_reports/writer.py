# basedpyright residual burn-down (shrink-only product surface).
"""Filesystem writers for pipeline/workflow run reports."""

from __future__ import annotations

import json
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
    REPORT_ROOT_MARKER_VALUE,
    inspect_report_root_marker,
    report_root_marker_is_healthy,
    report_root_marker_path,
    resolve_report_root,
)
from bioetl.domain.ports.storage.run_report_store import RunReportStorePort
from bioetl.domain.run_reports.models import PipelineRunReport, WorkflowRunReport

__all__ = (
    "DEFAULT_REPORT_ROOT",
    "REPORT_ROOT_MARKER_NAME",
    "REPORT_ROOT_MARKER_VALUE",
    "RunReportWriteResult",
    "configure_run_report_store",
    "inspect_report_root_marker",
    "report_root_marker_is_healthy",
    "report_root_marker_path",
    "resolve_pipeline_report_dir",
    "resolve_report_root",
    "resolve_workflow_report_dir",
    "write_json",
    "write_pipeline_run_report",
    "write_workflow_run_report",
)

_injected_store: RunReportStorePort | None = None


@dataclass(frozen=True, slots=True)
class RunReportWriteResult:
    """Paths written for one report."""

    json_path: Path
    markdown_path: Path
    latest_path: Path | None = None


def configure_run_report_store(store: RunReportStorePort | None) -> None:
    """Bind the composition-owned run-report store for default write paths."""
    global _injected_store
    _injected_store = store


def _require_store(store: RunReportStorePort | None) -> RunReportStorePort:
    resolved = store if store is not None else _injected_store
    if resolved is None:
        raise TypeError(
            "Run-report writes require an injected RunReportStorePort. "
            "Compose FileRunReportStoreAdapter at the composition root."
        )
    return resolved


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


def _atomic_write_text(
    path: Path, content: str, *, store: RunReportStorePort | None = None
) -> None:
    """Atomically replace one UTF-8 text artifact through the store port."""
    writer = _require_store(store)
    writer.mkdir(path.parent)
    writer.write_text(path, content)


def write_json(
    path: Path,
    payload: Mapping[str, object],
    *,
    store: RunReportStorePort | None = None,
) -> None:
    """Write deterministic JSON through an atomic same-directory replacement."""
    _atomic_write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        store=store,
    )


def _with_self_artifacts(
    artifacts: tuple[dict[str, Any], ...],
    *,
    json_path: Path,
    markdown_path: Path,
) -> tuple[dict[str, Any], ...]:
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
    payload: dict[str, Any],
    store: RunReportStorePort,
) -> Path:
    latest_path = owner_dir / "_latest.json"
    write_json(latest_path, payload, store=store)
    return latest_path


def write_pipeline_run_report(
    report: PipelineRunReport,
    *,
    root: Path | None = None,
    directory: Path | None = None,
    store: RunReportStorePort | None = None,
) -> RunReportWriteResult:
    """Write JSON + markdown pipeline run report artifacts and `_latest` pointer."""
    identity = report.identity
    resolved_dir = resolve_pipeline_report_dir(
        pipeline_name=str(identity.get("pipeline_name", "pipeline")),
        run_id=str(identity.get("run_id", "run")),
        root=root,
    )
    out_dir = directory or resolved_dir
    writer = _require_store(store)
    writer.mkdir(out_dir)
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
    write_json(json_path, enriched.to_dict(), store=writer)
    _atomic_write_text(
        md_path,
        render_pipeline_run_report_markdown(enriched),
        store=writer,
    )
    latest_path = _write_latest_pointer(
        owner_dir=resolved_dir.parent,
        payload={
            "kind": "pipeline_run_report",
            "pipeline_name": identity.get("pipeline_name"),
            "run_id": identity.get("run_id"),
            "status": identity.get("status"),
            "completed_at": identity.get("completed_at"),
            "json_path": str(json_path.as_posix()),
            "markdown_path": str(md_path.as_posix()),
        },
        store=writer,
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
    store: RunReportStorePort | None = None,
) -> RunReportWriteResult:
    """Write JSON + markdown workflow run report artifacts and `_latest` pointer."""
    identity = report.identity
    resolved_dir = resolve_workflow_report_dir(
        workflow_name=str(identity.get("workflow_name", "workflow")),
        workflow_run_id=str(identity.get("workflow_run_id") or "unknown"),
        root=root,
    )
    out_dir = directory or resolved_dir
    writer = _require_store(store)
    writer.mkdir(out_dir)
    json_path = out_dir / "workflow-run-report.json"
    md_path = out_dir / "workflow-run-report.md"
    write_json(json_path, report.to_dict(), store=writer)
    _atomic_write_text(
        md_path, render_workflow_run_report_markdown(report), store=writer
    )
    latest_path = _write_latest_pointer(
        owner_dir=resolved_dir.parent,
        payload={
            "kind": "workflow_run_report",
            "workflow_name": identity.get("workflow_name"),
            "workflow_run_id": identity.get("workflow_run_id"),
            "status": identity.get("status"),
            "completed_at": identity.get("completed_at"),
            "json_path": str(json_path.as_posix()),
            "markdown_path": str(md_path.as_posix()),
        },
        store=writer,
    )
    return RunReportWriteResult(
        json_path=json_path,
        markdown_path=md_path,
        latest_path=latest_path,
    )
