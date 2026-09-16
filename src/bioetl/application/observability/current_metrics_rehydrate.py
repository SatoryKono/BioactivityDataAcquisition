"""Rehydrate current-metrics from durable reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.observability.current_metrics_rehydrate_payload import (
    anchor_from_workflow_entry,
    first_text,
    load_report_payload,
)
from bioetl.application.observability.rehydrate_models import (
    PipelineRunSnapshot,
    RehydrateResult,
    WorkflowRunSnapshot,
)
from bioetl.application.services.run_reports.query import (
    ReportIndexEntry,
    list_pipeline_reports,
    list_workflow_reports,
)
from bioetl.domain.ports import RunReportStorePort

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

_TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown"})
_SEEDED_RUN_KEYS: set[tuple[str, str, str]] = set()
_SEEDED_PROVIDER_KEYS: set[str] = set()
_SEEDED_WORKFLOW_KEYS: set[str] = set()
_SEEDED_WORKFLOW_PIPELINE_KEYS: set[tuple[str, str, str, str]] = set()


def reset_rehydrate_seed_state() -> None:
    """Clear process-local seed memory (tests only)."""
    _SEEDED_RUN_KEYS.clear()
    _SEEDED_PROVIDER_KEYS.clear()
    _SEEDED_WORKFLOW_KEYS.clear()
    _SEEDED_WORKFLOW_PIPELINE_KEYS.clear()


def _persisted_unix(completed_at: str, fallback_mtime: float) -> float:
    """Prefer the report's completed_at; fall back to the artifact mtime."""
    if completed_at:
        try:
            return datetime.fromisoformat(completed_at).timestamp()
        except ValueError:
            pass
    return float(fallback_mtime)


def _anchor_from_report_entry(
    entry: ReportIndexEntry, *, store: RunReportStorePort
) -> PipelineRunSnapshot | None:
    """Build one terminal anchor from a report index entry, or None."""
    payload = load_report_payload(entry.json_path, store=store)
    if payload is None:
        return None
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        return None
    pipeline = first_text(identity.get("pipeline_name"), entry.owner)
    run_type = first_text(identity.get("run_type"))
    status = first_text(identity.get("status"), entry.status)
    run_id = first_text(identity.get("run_id"), entry.run_id)
    if not pipeline or not run_type or status not in _TERMINAL_STATUSES:
        return None
    provider_raw = identity.get("provider")
    provider = provider_raw.strip() if isinstance(provider_raw, str) else None
    completed = first_text(identity.get("completed_at"), entry.completed_at)
    return PipelineRunSnapshot(
        pipeline=pipeline,
        run_type=run_type,
        status=status,
        provider=provider or None,
        run_id=run_id,
        observed_unix=_persisted_unix(completed, entry.mtime),
    )


def collect_latest_terminal_anchors(
    *, root: Path | None = None, limit: int = 200, store: RunReportStorePort
) -> tuple[PipelineRunSnapshot, ...]:
    """Return one latest terminal anchor per pipeline × run_type × status."""
    entries = list_pipeline_reports(
        pipeline_name=None, limit=limit, root=root, store=store
    )
    selected: dict[tuple[str, str, str], PipelineRunSnapshot] = {}
    for entry in entries:
        anchor = _anchor_from_report_entry(entry, store=store)
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
    store: RunReportStorePort,
    include_pipeline_scopes: bool = True,
) -> tuple[WorkflowRunSnapshot, ...]:
    """Return one latest terminal anchor per workflow_name."""
    entries = list_workflow_reports(
        workflow_name=None, limit=limit, root=root, store=store
    )
    selected: dict[str, WorkflowRunSnapshot] = {}
    for entry in entries:
        anchor = anchor_from_workflow_entry(
            entry,
            root=root,
            store=store,
            include_pipeline_scopes=include_pipeline_scopes,
        )
        if anchor is None:
            continue
        if anchor.workflow in selected:
            continue
        selected[anchor.workflow] = anchor
    return tuple(selected.values())


def rehydrate_current_pipeline_run_metrics(
    metrics: MetricsPort, *, root: Path | None = None, store: RunReportStorePort
) -> RehydrateResult:
    """Ensure scraped contract samples exist for latest terminal runs."""
    try:
        anchors = collect_latest_terminal_anchors(root=root, store=store)
        workflow_anchors = collect_latest_terminal_workflow_anchors(
            root=root, store=store
        )
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
