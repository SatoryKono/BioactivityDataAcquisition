"""Load persisted run reports for HTTP ops endpoints."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from bioetl.application.services.run_reports.query import (
    ReportIndexEntry,
    list_pipeline_reports,
    list_workflow_reports,
)
from bioetl.domain.types import JsonDict
from bioetl.interfaces.http.report_root_config import (
    configured_report_root,
    report_root_readiness_check,
)

IndexKind = Literal["pipeline", "workflow"]
IndexState = Literal[
    "ok",
    "valid_empty",
    "tree_missing",
    "layout_unhealthy",
    "identity_unhealthy",
]

_INDEX_STATE_STATUS: Mapping[str, str] = {
    "tree_missing": "TREE_MISSING",
    "layout_unhealthy": "LAYOUT_UNHEALTHY",
    "identity_unhealthy": "IDENTITY_UNHEALTHY",
}
_VERIFY_BIND_HINT = (
    "From the checkout you are viewing run: "
    "python scripts/ops/runtime/docker/verify_report_bind.py --pipeline chembl_assay"
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
) -> JsonDict | None:
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
) -> JsonDict | None:
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


def _classify_index_state(
    *,
    kind: IndexKind,
    entry_count: int,
    root: Path,
    diagnostics: Mapping[str, object],
) -> tuple[IndexState, str]:
    """Distinguish a valid empty index from a missing or unhealthy tree."""
    if entry_count > 0:
        return "ok", f"{kind}-run-report index has matching artifacts."
    kind_root = root / kind
    if not root.exists() or not kind_root.is_dir():
        return (
            "tree_missing",
            (
                f"Ops HTTP has no {kind} run-reports tree at {root.as_posix()}. "
                f"{_VERIFY_BIND_HINT}"
            ),
        )
    if diagnostics.get("layout_status") != "healthy":
        layout_message = diagnostics.get("layout_message") or diagnostics.get("message")
        return (
            "layout_unhealthy",
            f"{layout_message or 'Report-root layout is unhealthy.'} {_VERIFY_BIND_HINT}",
        )
    if diagnostics.get("source_identity_status") != "healthy":
        identity_message = diagnostics.get("source_identity_message")
        return (
            "identity_unhealthy",
            (
                f"{identity_message or 'Report-root source identity is unhealthy.'} "
                f"{_VERIFY_BIND_HINT}"
            ),
        )
    return (
        "valid_empty",
        f"No matching {kind}-run-report artifacts under {kind_root.as_posix()}.",
    )


def _concrete_run_id(value: str | None) -> str | None:
    token = (value or "").strip()
    if token in {"", "-"}:
        return None
    return token


def _run_index_item(
    kind: IndexKind,
    item: ReportIndexEntry,
    *,
    selected_run_id: str | None = None,
) -> JsonDict:
    selected = (
        1 if selected_run_id is not None and item.run_id == selected_run_id else 0
    )
    paths = {
        "status": item.status,
        "completed_at": item.completed_at,
        "selected": selected,
        "json_path": str(item.json_path.as_posix()),
        "markdown_path": (
            str(item.markdown_path.as_posix()) if item.markdown_path else None
        ),
    }
    if kind == "workflow":
        return {"workflow": item.owner, "workflow_run_id": item.run_id, **paths}
    return {"pipeline": item.owner, "run_id": item.run_id, **paths}


def _diagnostic_index_item(
    *,
    kind: IndexKind,
    owner: str | None,
    index_state: IndexState,
    message: str,
) -> JsonDict:
    owner_value = owner or "-"
    row: JsonDict = {
        "row_kind": "diagnostic",
        "status": _INDEX_STATE_STATUS[index_state],
        "completed_at": None,
        "selected": 0,
        "json_path": None,
        "markdown_path": None,
        "message": message,
    }
    if kind == "workflow":
        row["workflow"] = owner_value
        row["workflow_run_id"] = "-"
        return row
    row["pipeline"] = owner_value
    row["run_id"] = "-"
    return row


def _index_items(
    *,
    kind: IndexKind,
    owner: str | None,
    entries: Sequence[ReportIndexEntry],
    index_state: IndexState,
    message: str,
    selected_run_id: str | None = None,
) -> list[JsonDict]:
    if entries:
        return [
            _run_index_item(kind, item, selected_run_id=selected_run_id)
            for item in entries
        ]
    if index_state == "valid_empty":
        return []
    return [
        _diagnostic_index_item(
            kind=kind,
            owner=owner,
            index_state=index_state,
            message=message,
        )
    ]


def _list_report_payload(
    *,
    kind: IndexKind,
    owner: str | None,
    entries: Sequence[ReportIndexEntry],
    root: Path,
    selected_run_id: str | None = None,
) -> JsonDict:
    diagnostics = report_root_readiness_check(root=root)
    index_state, index_message = _classify_index_state(
        kind=kind,
        entry_count=len(entries),
        root=root,
        diagnostics=diagnostics,
    )
    return {
        "status": "ok",
        "count": len(entries),
        "index_state": index_state,
        "index_state_message": index_message,
        "report_root": str(root.as_posix()),
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
        "items": _index_items(
            kind=kind,
            owner=owner,
            entries=entries,
            index_state=index_state,
            message=index_message,
            selected_run_id=selected_run_id,
        ),
    }


def list_pipeline_run_report_payloads(
    *,
    pipeline_name: str | None = None,
    limit: int = 20,
    root: Path | None = None,
    selected_run_id: str | None = None,
) -> JsonDict:
    """List recent pipeline run reports (index only, not full bodies)."""
    base = _effective_root(root)
    owner = _normalize_list_owner(pipeline_name)
    entries = list_pipeline_reports(
        pipeline_name=owner,
        limit=limit,
        root=base,
    )
    return _list_report_payload(
        kind="pipeline",
        owner=owner,
        entries=entries,
        root=base,
        selected_run_id=_concrete_run_id(selected_run_id),
    )


def list_workflow_run_report_payloads(
    *,
    workflow_name: str | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> JsonDict:
    """List recent workflow run reports (index only)."""
    base = _effective_root(root)
    owner = _normalize_list_owner(workflow_name)
    entries = list_workflow_reports(
        workflow_name=owner,
        limit=limit,
        root=base,
    )
    return _list_report_payload(
        kind="workflow",
        owner=owner,
        entries=entries,
        root=base,
    )


def _load_versioned_payload(
    path: Path,
    *,
    expected_schema: str,
) -> JsonDict | None:
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
