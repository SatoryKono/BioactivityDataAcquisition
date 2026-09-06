"""Rehydrate scraped current-metrics samples from durable run reports.

CLI pipeline processes increment ``bioetl_pipeline_runs_total`` in-process.
The long-lived ``bioetl health server`` scrape registry is a different process
and otherwise emits HELP/TYPE without samples, which trips
``absent_over_time(bioetl_pipeline_runs_total[10m])``.

Workflow CLI publishes ``bioetl_workflow_expected`` in-process the same way.
Grafana ``$workflow`` is ``label_values(bioetl_workflow_universe, workflow)``
over the dashboard range and stays All-only until the health-server scrape
has a sample.

This module publishes CURRENT gauges from the latest terminal pipeline-run
and workflow-run reports. It never increments RANGE event counters by a
positive amount and does not invent ``run_id`` labels. Presence-only ``0``
samples of ``bioetl_pipeline_runs_total`` are allowed so scrape is not
HELP/TYPE-only and ``increase()`` stays zero until a real in-process run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.run_reports.query import (
    ReportIndexEntry,
    list_pipeline_reports,
    list_workflow_reports,
    load_pipeline_report,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

_TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown"})
_WORKFLOW_TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown"})
_SEEDED_RUN_KEYS: set[tuple[str, str, str]] = set()
_SEEDED_PROVIDER_KEYS: set[str] = set()
_SEEDED_WORKFLOW_KEYS: set[str] = set()
_SEEDED_WORKFLOW_PIPELINE_KEYS: set[tuple[str, str, str, str]] = set()


@dataclass(frozen=True, slots=True)
class PipelineRunSnapshot:
    """Latest terminal run identity used to seed current-metric samples."""

    pipeline: str
    run_type: str
    status: str
    provider: str | None
    run_id: str
    observed_unix: float


@dataclass(frozen=True, slots=True)
class WorkflowPipelineScope:
    """One planned pipeline scope from a terminal workflow report."""

    pipeline: str
    run_type: str
    provider: str


@dataclass(frozen=True, slots=True)
class WorkflowRunSnapshot:
    """Latest terminal workflow identity used to seed selector gauges."""

    workflow: str
    status: str
    provider: str
    run_id: str
    pipelines: tuple[WorkflowPipelineScope, ...]


@dataclass(frozen=True, slots=True)
class RehydrateResult:
    """Outcome of one rehydrate pass."""

    anchors: int
    pipeline_runs_seeded: int
    provider_universe_seeded: int
    stage_series_seeded: int
    workflow_anchors: int = 0
    workflow_expected_seeded: int = 0
    workflow_pipeline_expected_seeded: int = 0
    error: str | None = None


def reset_rehydrate_seed_state() -> None:
    """Clear process-local seed memory (tests only)."""
    _SEEDED_RUN_KEYS.clear()
    _SEEDED_PROVIDER_KEYS.clear()
    _SEEDED_WORKFLOW_KEYS.clear()
    _SEEDED_WORKFLOW_PIPELINE_KEYS.clear()


def _first_text(*values: object) -> str:
    """Return the first non-empty stripped string from *values*."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _persisted_unix(completed_at: str, fallback_mtime: float) -> float:
    """Prefer the report's completed_at; fall back to the artifact mtime."""
    if completed_at:
        try:
            return datetime.fromisoformat(completed_at).timestamp()
        except ValueError:
            pass
    return float(fallback_mtime)


def _provider_from_pipeline_name(pipeline_name: str) -> str:
    """Derive the bounded provider label from ``provider_entity`` names."""
    provider, separator, _entity = pipeline_name.partition("_")
    if separator and provider:
        return provider
    return pipeline_name or "unknown"


def _anchor_from_report_entry(entry: ReportIndexEntry) -> PipelineRunSnapshot | None:
    """Build one terminal anchor from a report index entry, or None."""
    payload = _load_report_payload(entry.json_path)
    if payload is None:
        return None
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        return None
    pipeline = _first_text(identity.get("pipeline_name"), entry.owner)
    run_type = _first_text(identity.get("run_type"))
    status = _first_text(identity.get("status"), entry.status)
    run_id = _first_text(identity.get("run_id"), entry.run_id)
    if not pipeline or not run_type or status not in _TERMINAL_STATUSES:
        return None
    provider_raw = identity.get("provider")
    provider = provider_raw.strip() if isinstance(provider_raw, str) else None
    completed = _first_text(identity.get("completed_at"), entry.completed_at)
    return PipelineRunSnapshot(
        pipeline=pipeline,
        run_type=run_type,
        status=status,
        provider=provider or None,
        run_id=run_id,
        observed_unix=_persisted_unix(completed, entry.mtime),
    )


def collect_latest_terminal_anchors(
    *,
    root: Path | None = None,
    limit: int = 200,
) -> tuple[PipelineRunSnapshot, ...]:
    """Return one latest terminal anchor per pipeline × run_type × status."""
    entries = list_pipeline_reports(pipeline_name=None, limit=limit, root=root)
    selected: dict[tuple[str, str, str], PipelineRunSnapshot] = {}
    for entry in entries:
        anchor = _anchor_from_report_entry(entry)
        if anchor is None:
            continue
        key = (anchor.pipeline, anchor.run_type, anchor.status)
        if key in selected:
            continue
        selected[key] = anchor
    return tuple(selected.values())


def collect_latest_terminal_workflow_anchors(
    *,
    root: Path | None = None,
    limit: int = 200,
) -> tuple[WorkflowRunSnapshot, ...]:
    """Return one latest terminal anchor per workflow_name."""
    entries = list_workflow_reports(workflow_name=None, limit=limit, root=root)
    selected: dict[str, WorkflowRunSnapshot] = {}
    for entry in entries:
        anchor = _anchor_from_workflow_entry(entry, root=root)
        if anchor is None:
            continue
        if anchor.workflow in selected:
            continue
        selected[anchor.workflow] = anchor
    return tuple(selected.values())


def rehydrate_current_pipeline_run_metrics(
    metrics: MetricsPort,
    *,
    root: Path | None = None,
) -> RehydrateResult:
    """Ensure scraped contract samples exist for latest terminal runs."""
    try:
        anchors = collect_latest_terminal_anchors(root=root)
        workflow_anchors = collect_latest_terminal_workflow_anchors(root=root)
        runs_seeded = 0
        providers_seeded = 0
        stages_seeded = 0
        workflow_expected_seeded = 0
        workflow_pipeline_expected_seeded = 0
        for anchor in anchors:
            runs_seeded += _seed_pipeline_runs_total(metrics, anchor)
            providers_seeded += _seed_provider_universe(metrics, anchor)
            stages_seeded += _seed_stage_series(metrics, anchor)
        for workflow_anchor in workflow_anchors:
            workflow_expected_seeded += _seed_workflow_expected(
                metrics, workflow_anchor
            )
            workflow_pipeline_expected_seeded += _seed_workflow_pipeline_expected(
                metrics,
                workflow_anchor,
            )
        return RehydrateResult(
            anchors=len(anchors),
            pipeline_runs_seeded=runs_seeded,
            provider_universe_seeded=providers_seeded,
            stage_series_seeded=stages_seeded,
            workflow_anchors=len(workflow_anchors),
            workflow_expected_seeded=workflow_expected_seeded,
            workflow_pipeline_expected_seeded=workflow_pipeline_expected_seeded,
        )
    except (
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        return RehydrateResult(
            anchors=0,
            pipeline_runs_seeded=0,
            provider_universe_seeded=0,
            stage_series_seeded=0,
            error=str(exc),
        )


def _seed_pipeline_runs_total(metrics: MetricsPort, anchor: PipelineRunSnapshot) -> int:
    key = (anchor.pipeline, anchor.run_type, anchor.status)
    if key in _SEEDED_RUN_KEYS:
        return 0
    labels = {"pipeline": anchor.pipeline, "run_type": anchor.run_type}
    metrics.set_gauge("bioetl_control_plane_manifest_present", 1.0, labels)
    metrics.set_gauge("bioetl_control_plane_ledger_present", 1.0, labels)
    metrics.set_gauge("bioetl_control_plane_integrity_pair_present", 1.0, labels)
    metrics.set_gauge("bioetl_control_plane_checkpoint_present", 0.0, labels)
    metrics.set_gauge(
        "bioetl_control_plane_last_observed_timestamp_seconds",
        float(anchor.observed_unix),
        labels,
    )
    # Presence-only: labeled scrape sample without faking increase().
    metrics.increment_counter(
        "bioetl_pipeline_runs_total",
        0,
        {
            "pipeline": anchor.pipeline,
            "run_type": anchor.run_type,
            "status": anchor.status,
        },
    )
    _SEEDED_RUN_KEYS.add(key)
    return 1


def _seed_provider_universe(metrics: MetricsPort, anchor: PipelineRunSnapshot) -> int:
    provider = anchor.provider
    if provider is None or provider in _SEEDED_PROVIDER_KEYS:
        return 0
    metrics.set_gauge(
        "bioetl_provider_observed_universe",
        1.0,
        {"provider": provider},
    )
    _SEEDED_PROVIDER_KEYS.add(provider)
    return 1


def _seed_stage_series(metrics: MetricsPort, anchor: PipelineRunSnapshot) -> int:
    del metrics, anchor
    return 0


def _seed_workflow_expected(
    metrics: MetricsPort,
    anchor: WorkflowRunSnapshot,
) -> int:
    if anchor.workflow in _SEEDED_WORKFLOW_KEYS:
        return 0
    metrics.set_gauge(
        "bioetl_workflow_expected",
        1.0,
        {"workflow": anchor.workflow, "provider": anchor.provider},
    )
    _SEEDED_WORKFLOW_KEYS.add(anchor.workflow)
    return 1


def _seed_workflow_pipeline_expected(
    metrics: MetricsPort,
    anchor: WorkflowRunSnapshot,
) -> int:
    seeded = 0
    for scope in anchor.pipelines:
        key = (anchor.workflow, scope.pipeline, scope.run_type, scope.provider)
        if key in _SEEDED_WORKFLOW_PIPELINE_KEYS:
            continue
        metrics.set_gauge(
            "bioetl_workflow_pipeline_expected",
            1.0,
            {
                "workflow": anchor.workflow,
                "pipeline": scope.pipeline,
                "run_type": scope.run_type,
                "provider": scope.provider,
            },
        )
        _SEEDED_WORKFLOW_PIPELINE_KEYS.add(key)
        seeded += 1
    return seeded


def _anchor_from_workflow_entry(
    entry: ReportIndexEntry,
    *,
    root: Path | None,
) -> WorkflowRunSnapshot | None:
    """Build one terminal workflow anchor, or None."""
    payload = _load_report_payload(entry.json_path)
    if payload is None:
        return None
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        return None
    workflow = _first_text(
        identity.get("workflow_name"),
        entry.owner,
        entry.workflow_id,
    )
    status = _first_text(identity.get("status"), entry.status)
    run_id = _first_text(
        identity.get("workflow_run_id"),
        entry.workflow_run_id,
        entry.run_id,
    )
    if not workflow or status not in _WORKFLOW_TERMINAL_STATUSES:
        return None
    pipelines = _pipeline_scopes_from_payload(payload, root=root)
    provider = _workflow_provider(payload, pipelines)
    return WorkflowRunSnapshot(
        workflow=workflow,
        status=status,
        provider=provider,
        run_id=run_id,
        pipelines=pipelines,
    )


def _workflow_provider(
    payload: dict[str, object],
    pipelines: tuple[WorkflowPipelineScope, ...],
) -> str:
    if pipelines:
        return pipelines[0].provider
    for pipeline_name in _pipeline_names_from_payload(payload):
        return _provider_from_pipeline_name(pipeline_name)
    return "unknown"


def _collect_pipeline_names(rows: object, seen: set[str], names: list[str]) -> None:
    if not isinstance(rows, list):
        return
    for row in rows:
        if isinstance(row, dict):
            pipeline = _first_text(row.get("pipeline_name"))
            if pipeline and pipeline not in seen:
                seen.add(pipeline)
                names.append(pipeline)


def _pipeline_names_from_payload(payload: dict[str, object]) -> tuple[str, ...]:
    names: list[str] = []
    seen: set[str] = set()
    _collect_pipeline_names(payload.get("execution"), seen, names)
    plan = payload.get("plan")
    if isinstance(plan, dict):
        _collect_pipeline_names(plan.get("steps"), seen, names)
    return tuple(names)


def _pipeline_scopes_from_payload(
    payload: dict[str, object],
    *,
    root: Path | None,
) -> tuple[WorkflowPipelineScope, ...]:
    selected: dict[tuple[str, str, str], WorkflowPipelineScope] = {}
    execution = payload.get("execution")
    if not isinstance(execution, list):
        return ()
    for row in execution:
        if not isinstance(row, dict):
            continue
        pipeline = _first_text(row.get("pipeline_name"))
        if not pipeline:
            continue
        run_type = _run_type_from_execution_row(row, pipeline=pipeline, root=root)
        if not run_type:
            continue
        provider = _provider_from_pipeline_name(pipeline)
        key = (pipeline, run_type, provider)
        if key in selected:
            continue
        selected[key] = WorkflowPipelineScope(
            pipeline=pipeline,
            run_type=run_type,
            provider=provider,
        )
    return tuple(selected.values())


def _run_type_from_execution_row(
    row: dict[str, object],
    *,
    pipeline: str,
    root: Path | None,
) -> str:
    explicit = _first_text(row.get("run_type"))
    if explicit:
        return explicit
    pipeline_run_id = _first_text(row.get("pipeline_run_id"))
    if not pipeline_run_id:
        return ""
    child = load_pipeline_report(
        pipeline_name=pipeline,
        run_id=pipeline_run_id,
        root=root,
    )
    if not isinstance(child, dict):
        return ""
    identity = child.get("identity")
    if not isinstance(identity, dict):
        return ""
    return _first_text(identity.get("run_type"))


def _load_report_payload(path: Path) -> dict[str, object] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        import json

        payload = json.loads(text)
    except (UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None
