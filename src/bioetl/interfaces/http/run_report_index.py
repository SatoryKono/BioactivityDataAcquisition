"""Index item builders for HTTP run-report listing endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from bioetl.application.services.run_reports.query import ReportIndexEntry
from bioetl.domain.types import JsonDict

IndexKind = Literal["pipeline", "workflow"]
IndexState = Literal[
    "ok",
    "valid_empty",
    "tree_missing",
    "layout_unhealthy",
    "identity_unhealthy",
]

_VERIFY_BIND_HINT = (
    "From the checkout you are viewing run: "
    "python scripts/ops/runtime/docker/verify_report_bind.py --pipeline chembl_assay"
)

__all__ = [
    "_VERIFY_BIND_HINT",
    "IndexKind",
    "IndexState",
    "_classify_index_state",
    "_concrete_run_id",
    "_index_optional_label",
    "_normalize_list_owner",
    "_run_index_item",
]


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
        "processing_status": item.status,
        # Trust/evidence is a separate axis on 1. Trust; index stays execution-only.
        "trust_status": "Inspect in 1. Trust",
        "completed_at": item.completed_at,
        "selected": selected,
        "json_path": str(item.json_path.as_posix()),
        "markdown_path": (
            str(item.markdown_path.as_posix()) if item.markdown_path else None
        ),
    }
    if kind == "workflow":
        if item.schema_version != "workflow_run_report_v1":
            reason = (
                "schema_mismatch"
                if item.schema_version is not None
                else "report_invalid_or_unreadable"
            )
            status = "SCHEMA_MISMATCH" if item.schema_version else "REPORT_INVALID"
            return {
                "row_kind": "diagnostic",
                "workflow": item.owner,
                "workflow_run_id": item.run_id,
                **paths,
                "status": status,
                "processing_status": status,
                "trust_status": "QUERY ERROR",
                "reason": reason,
                "expected_schema": "workflow_run_report_v1",
                "actual_schema": item.schema_version,
                "message": (
                    "Persisted workflow report does not satisfy "
                    "workflow_run_report_v1; the original artifact was preserved."
                ),
            }
        return {"workflow": item.owner, "workflow_run_id": item.run_id, **paths}
    return {
        "pipeline": item.owner,
        "run_id": item.run_id,
        "workflow_id": _index_optional_label(item.workflow_id),
        "workflow_run_id": _index_optional_label(item.workflow_run_id),
        "started_at": item.started_at,
        "run_type": item.run_type,
        **paths,
    }


def _index_optional_label(value: str | None) -> str:
    """Compact identity label for the pipeline index; empty is emdash, not VALID EMPTY."""
    token = (value or "").strip()
    return token if token else "—"
