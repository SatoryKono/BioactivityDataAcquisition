"""Report payload helpers for current-metrics rehydrate."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.application.observability.rehydrate_models import (
    WorkflowPipelineScopeInfo,
    WorkflowRunSnapshot,
)
from bioetl.application.services.run_reports.query import (
    ReportIndexEntry,
    load_pipeline_report,
)
from bioetl.domain.ports import RunReportStorePort

_WORKFLOW_TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown"})


def first_text(*values: object) -> str:
    """Return the first non-empty stripped string from *values*."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def provider_from_pipeline_name(pipeline_name: str) -> str:
    """Derive the bounded provider label from ``provider_entity`` names."""
    provider, separator, _entity = pipeline_name.partition("_")
    if separator and provider:
        return provider
    return pipeline_name or "unknown"


def load_report_payload(
    path: Path, *, store: RunReportStorePort
) -> dict[str, object] | None:
    try:
        text = store.read_text(str(path))
    except OSError:
        return None
    try:
        payload = json.loads(text)
    except (UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def anchor_from_workflow_entry(
    entry: ReportIndexEntry,
    *,
    root: Path | None,
    store: RunReportStorePort,
    include_pipeline_scopes: bool = True,
) -> WorkflowRunSnapshot | None:
    """Build one terminal workflow anchor, or None."""
    payload = load_report_payload(entry.json_path, store=store)
    if payload is None:
        return None
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        return None
    workflow = first_text(
        identity.get("workflow_name"),
        entry.owner,
        entry.workflow_id,
    )
    status = first_text(identity.get("status"), entry.status)
    run_id = first_text(
        identity.get("workflow_run_id"),
        entry.workflow_run_id,
        entry.run_id,
    )
    if not workflow or status not in _WORKFLOW_TERMINAL_STATUSES:
        return None
    pipelines = (
        pipeline_scopes_from_payload(payload, root=root, store=store)
        if include_pipeline_scopes
        else ()
    )
    provider = workflow_provider(payload, pipelines)
    return WorkflowRunSnapshot(
        workflow=workflow,
        status=status,
        provider=provider,
        run_id=run_id,
        pipelines=pipelines,
    )


def workflow_provider(
    payload: dict[str, object],
    pipelines: tuple[WorkflowPipelineScopeInfo, ...],
) -> str:
    if pipelines:
        return pipelines[0].provider
    for pipeline_name in pipeline_names_from_payload(payload):
        return provider_from_pipeline_name(pipeline_name)
    return "unknown"


def _collect_pipeline_names(rows: object, seen: set[str], names: list[str]) -> None:
    if not isinstance(rows, list):
        return
    for row in rows:
        if isinstance(row, dict):
            pipeline = first_text(row.get("pipeline_name"))
            if pipeline and pipeline not in seen:
                seen.add(pipeline)
                names.append(pipeline)


def pipeline_names_from_payload(payload: dict[str, object]) -> tuple[str, ...]:
    names: list[str] = []
    seen: set[str] = set()
    _collect_pipeline_names(payload.get("execution"), seen, names)
    plan = payload.get("plan")
    if isinstance(plan, dict):
        _collect_pipeline_names(plan.get("steps"), seen, names)
    return tuple(names)


def pipeline_scopes_from_payload(
    payload: dict[str, object], *, root: Path | None, store: RunReportStorePort
) -> tuple[WorkflowPipelineScopeInfo, ...]:
    selected: dict[tuple[str, str, str], WorkflowPipelineScopeInfo] = {}
    execution = payload.get("execution")
    if not isinstance(execution, list):
        return ()
    for row in execution:
        if not isinstance(row, dict):
            continue
        pipeline = first_text(row.get("pipeline_name"))
        if not pipeline:
            continue
        run_type = run_type_from_execution_row(
            row, pipeline=pipeline, root=root, store=store
        )
        if not run_type:
            continue
        provider = provider_from_pipeline_name(pipeline)
        key = (pipeline, run_type, provider)
        if key in selected:
            continue
        selected[key] = WorkflowPipelineScopeInfo(
            pipeline=pipeline,
            run_type=run_type,
            provider=provider,
        )
    return tuple(selected.values())


def run_type_from_execution_row(
    row: dict[str, object],
    *,
    pipeline: str,
    root: Path | None,
    store: RunReportStorePort,
) -> str:
    explicit = first_text(row.get("run_type"))
    if explicit:
        return explicit
    pipeline_run_id = first_text(row.get("pipeline_run_id"))
    if not pipeline_run_id:
        return ""
    child = load_pipeline_report(
        pipeline_name=pipeline, run_id=pipeline_run_id, root=root, store=store
    )
    if not isinstance(child, dict):
        return ""
    identity = child.get("identity")
    if not isinstance(identity, dict):
        return ""
    return first_text(identity.get("run_type"))
