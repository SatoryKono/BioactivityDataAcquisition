"""Load persisted run reports for HTTP ops endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bioetl.application.services.run_reports.query import (
    list_pipeline_reports,
    list_workflow_reports,
)
from bioetl.interfaces.http.report_root_config import (
    configured_report_root,
    report_root_readiness_check,
)


def _safe_segment(value: str) -> str:
    """Sanitize one path segment and reject dot-only traversal tokens."""
    text = value.strip()
    # Fail closed on relative/parent segments rather than rewriting them.
    if text in {".", ".."} or text.startswith(".."):
        raise ValueError(f"invalid path segment: {value!r}")
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)
    if cleaned in {".", ".."} or not cleaned:
        raise ValueError(f"invalid path segment: {value!r}")
    return cleaned[:120]


def _effective_root(root: Path | None) -> Path:
    return configured_report_root(root=root)


def load_pipeline_run_report_payload(
    *,
    run_id: str,
    pipeline_name: str | None = None,
    root: Path | None = None,
) -> dict[str, Any] | None:  # Any: report/json payload shape is dynamic
    """Load pipeline-run-report.json from local reports tree."""
    if pipeline_name is None:
        return None
    try:
        safe_pipeline = _safe_segment(pipeline_name)
        safe_run_id = _safe_segment(run_id)
    except ValueError:
        return None
    base = _effective_root(root)
    path = base / "pipeline" / safe_pipeline / safe_run_id / "pipeline-run-report.json"
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
    try:
        safe_workflow = _safe_segment(workflow_name)
        safe_run_id = _safe_segment(workflow_run_id)
    except ValueError:
        return None
    base = _effective_root(root)
    path = base / "workflow" / safe_workflow / safe_run_id / "workflow-run-report.json"
    return _load_versioned_payload(path, expected_schema="workflow_run_report_v1")


def _normalize_list_owner(name: str | None) -> str | None:
    """Treat Grafana All-scope tokens as unbounded list (all pipelines)."""
    if name is None:
        return None
    text = name.strip()
    if not text:
        return None
    lowered = text.casefold()
    if lowered in {"all", "*"} or text in {"$__all", "__all", "All", ".*"}:
        return None
    return text


def list_pipeline_run_report_payloads(
    *,
    pipeline_name: str | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> dict[str, Any]:  # Any: list payload
    """List recent pipeline run reports (index only, not full bodies)."""
    base = _effective_root(root)
    entries = list_pipeline_reports(
        pipeline_name=_normalize_list_owner(pipeline_name),
        limit=limit,
        root=base,
    )
    diagnostics = report_root_readiness_check(root=base)
    return {
        "status": "ok",
        "count": len(entries),
        "report_root": str(base.as_posix()),
        "marker": diagnostics.get("marker"),
        # Backward-compatible layout status for existing Grafana payloads.
        "marker_status": diagnostics.get("layout_status"),
        "source_identity": diagnostics.get("source_identity"),
        "source_identity_state": diagnostics.get("source_identity_state"),
        "source_identity_status": diagnostics.get("source_identity_status"),
        "source_identity_expected": diagnostics.get("source_identity_expected"),
        "source_identity_actual": diagnostics.get("source_identity_actual"),
        "source_identity_resolution_source": diagnostics.get(
            "source_identity_resolution_source"
        ),
        "items": [
            {
                "pipeline": item.owner,
                "run_id": item.run_id,
                "status": item.status,
                "completed_at": item.completed_at,
                "json_path": str(item.json_path.as_posix()),
                "markdown_path": (
                    str(item.markdown_path.as_posix()) if item.markdown_path else None
                ),
            }
            for item in entries
        ],
    }


def list_workflow_run_report_payloads(
    *,
    workflow_name: str | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> dict[str, Any]:  # Any: list payload
    """List recent workflow run reports (index only)."""
    base = _effective_root(root)
    entries = list_workflow_reports(
        workflow_name=_normalize_list_owner(workflow_name),
        limit=limit,
        root=base,
    )
    diagnostics = report_root_readiness_check(root=base)
    return {
        "status": "ok",
        "count": len(entries),
        "report_root": str(base.as_posix()),
        "marker": diagnostics.get("marker"),
        "marker_status": diagnostics.get("layout_status"),
        "source_identity": diagnostics.get("source_identity"),
        "source_identity_state": diagnostics.get("source_identity_state"),
        "source_identity_status": diagnostics.get("source_identity_status"),
        "source_identity_expected": diagnostics.get("source_identity_expected"),
        "source_identity_actual": diagnostics.get("source_identity_actual"),
        "source_identity_resolution_source": diagnostics.get(
            "source_identity_resolution_source"
        ),
        "items": [
            {
                "workflow": item.owner,
                "workflow_run_id": item.run_id,
                "status": item.status,
                "completed_at": item.completed_at,
                "json_path": str(item.json_path.as_posix()),
                "markdown_path": (
                    str(item.markdown_path.as_posix()) if item.markdown_path else None
                ),
            }
            for item in entries
        ],
    }


def _load_versioned_payload(
    path: Path,
    *,
    expected_schema: str,
) -> dict[str, Any] | None:  # Any: report/json payload shape is dynamic
    """Load one completed artifact and reject malformed/wrong-version payloads."""
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        # Partial writes / corrupt artifacts must not 500 the ops surface.
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != expected_schema
    ):
        return None
    return payload
