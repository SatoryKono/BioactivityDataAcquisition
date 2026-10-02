"""Load persisted run reports for HTTP ops endpoints."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from bioetl.application.services.run_reports.query import (
    ReportIndexEntry,
    list_pipeline_reports,
    list_workflow_reports,
)
from bioetl.composition.observability_runtime import create_run_report_store
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.types import JsonDict
from bioetl.interfaces.http.report_root_config import (
    configured_report_root,
    report_root_readiness_check,
)
from bioetl.interfaces.http.run_report_index import (
    IndexKind,
    IndexState,
    _classify_index_state,
    _concrete_run_id,
    _normalize_list_owner,
    _run_index_item,
)

_INDEX_STATE_STATUS: Mapping[str, str] = {
    "tree_missing": "TREE_MISSING",
    "layout_unhealthy": "LAYOUT_UNHEALTHY",
    "identity_unhealthy": "IDENTITY_UNHEALTHY",
}


class InvalidRunReportError(ValueError):
    """Describe one persisted report that exists but cannot satisfy its contract."""

    def __init__(
        self,
        *,
        reason: str,
        expected_schema: str,
        actual_schema: object = None,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.expected_schema = expected_schema
        self.actual_schema = actual_schema


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
    return _load_workflow_payload(path)


def _load_workflow_payload(path: Path) -> JsonDict | None:
    """Load a workflow report while distinguishing absence from invalid evidence."""
    expected_schema = "workflow_run_report_v1"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InvalidRunReportError(
            reason="malformed_json",
            expected_schema=expected_schema,
        ) from exc
    except UnicodeDecodeError as exc:
        raise InvalidRunReportError(
            reason="malformed_encoding",
            expected_schema=expected_schema,
        ) from exc
    except OSError as exc:
        raise InvalidRunReportError(
            reason="report_read_error",
            expected_schema=expected_schema,
        ) from exc
    if not isinstance(payload, dict):
        raise InvalidRunReportError(
            reason="invalid_payload",
            expected_schema=expected_schema,
        )
    actual_schema = payload.get("schema_version")
    if actual_schema != expected_schema:
        raise InvalidRunReportError(
            reason="schema_mismatch",
            expected_schema=expected_schema,
            actual_schema=actual_schema,
        )
    return payload


def load_pipeline_run_report_artifact(
    *, pipeline: str, run_id: str, artifact_format: str, root: Path | None = None
) -> str | None:
    """Read only the named run's JSON/Markdown report, never a caller path."""
    json_path, path = _validated_artifact_paths(pipeline, run_id, artifact_format, root)
    payload = _load_versioned_payload(
        json_path, expected_schema="pipeline_run_report_v1"
    )
    if payload is None or not path.is_file():
        return None
    identity = payload.get("identity")
    if not isinstance(identity, dict) or (
        identity.get("run_id") != run_id or identity.get("pipeline_name") != pipeline
    ):
        raise ValueError("report identity does not match the selected run")
    return path.read_text(encoding="utf-8")


def _validated_artifact_paths(
    pipeline: str, run_id: str, artifact_format: str, root: Path | None
) -> tuple[Path, Path]:
    """Resolve the supported artifact pair inside the exact selected run."""
    extensions = {"pipeline_run_report_json": "json", "pipeline_run_report_md": "md"}
    if artifact_format not in extensions:
        raise ValueError("unsupported report artifact format")
    if _safe_segment(pipeline) != pipeline or _safe_segment(run_id) != run_id:
        raise ValueError("invalid pipeline or run_id")
    base = _effective_root(root).resolve()
    run_root = (base / "pipeline" / pipeline / run_id).resolve()
    if not run_root.is_relative_to(base):
        raise ValueError("report path is outside the configured report root")
    json_path = (run_root / "pipeline-run-report.json").resolve()
    path = (run_root / f"pipeline-run-report.{extensions[artifact_format]}").resolve()
    if not path.is_relative_to(run_root) or not json_path.is_relative_to(run_root):
        raise ValueError("report artifact is outside the selected run")
    return json_path, path


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
    row["workflow_id"] = "—"
    row["workflow_run_id"] = "—"
    row["started_at"] = None
    row["run_type"] = None
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
    limit: int | None = 20,
    root: Path | None = None,
    selected_run_id: str | None = None,
    store: RunReportStorePort | None = None,
) -> JsonDict:
    """List recent pipeline run reports (index only, not full bodies)."""
    base = _effective_root(root)
    owner = _normalize_list_owner(pipeline_name)
    entries = list_pipeline_reports(
        pipeline_name=owner,
        limit=limit,
        root=base,
        store=store if store is not None else create_run_report_store(),
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
    store: RunReportStorePort | None = None,
) -> JsonDict:
    """List recent workflow run reports (index only)."""
    base = _effective_root(root)
    owner = _normalize_list_owner(workflow_name)
    entries = list_workflow_reports(
        workflow_name=owner,
        limit=limit,
        root=base,
        store=store if store is not None else create_run_report_store(),
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
    accepted = {expected_schema}
    if expected_schema == "pipeline_run_report_v1":
        accepted.add("pipeline_run_report_v2")
    if not isinstance(payload, dict) or payload.get("schema_version") not in accepted:
        return None
    return payload
