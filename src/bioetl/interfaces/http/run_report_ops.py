"""Load persisted run reports for HTTP ops endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bioetl.application.services.run_reports.writer import DEFAULT_REPORT_ROOT


def _safe_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
    return cleaned[:120] or "unknown"


def load_pipeline_run_report_payload(
    *,
    run_id: str,
    pipeline_name: str | None = None,
    root: Path | None = None,
) -> dict[str, Any] | None:  # Any: report/json payload shape is dynamic
    """Load pipeline-run-report.json from local reports tree."""
    if pipeline_name is None:
        return None
    base = root or DEFAULT_REPORT_ROOT
    path = (
        base
        / "pipeline"
        / _safe_segment(pipeline_name)
        / _safe_segment(run_id)
        / "pipeline-run-report.json"
    )
    return _load_versioned_payload(path, expected_schema="pipeline_run_report_v1")


def load_workflow_run_report_payload(
    *,
    workflow_run_id: str,
    workflow_name: str | None = None,
    root: Path | None = None,
) -> dict[str, Any] | None:  # Any: report/json payload shape is dynamic
    """Load workflow-run-report.json from local reports tree."""
    if workflow_name is None:
        return None
    base = root or DEFAULT_REPORT_ROOT
    path = (
        base
        / "workflow"
        / _safe_segment(workflow_name)
        / _safe_segment(workflow_run_id)
        / "workflow-run-report.json"
    )
    return _load_versioned_payload(path, expected_schema="workflow_run_report_v1")


def _load_versioned_payload(
    path: Path,
    *,
    expected_schema: str,
) -> dict[str, Any] | None:  # Any: report/json payload shape is dynamic
    """Load one completed artifact and reject malformed/wrong-version payloads."""
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != expected_schema:
        return None
    return payload
    return None
