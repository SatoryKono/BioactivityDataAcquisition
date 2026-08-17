"""Rehydrate scraped current-metrics samples from durable run reports.

CLI pipeline processes increment ``bioetl_pipeline_runs_total`` in-process.
The long-lived ``bioetl health server`` scrape registry is a different process
and otherwise emits HELP/TYPE without samples, which trips
``absent_over_time(bioetl_pipeline_runs_total[10m])``.

This module seeds existing contract families from the latest terminal
pipeline-run reports. It does not invent series names or ``run_id`` labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.run_reports.query import list_pipeline_reports

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

_TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown"})
_SEEDED_RUN_KEYS: set[tuple[str, str, str]] = set()
_SEEDED_PROVIDER_KEYS: set[str] = set()
_SEEDED_STAGE_KEYS: set[tuple[str, str, str, str]] = set()

_STAGE_OUTCOMES: tuple[tuple[str, str], ...] = (
    ("bronze", "records"),
    ("silver", "valid"),
    ("gold", "written"),
    ("gold", "excluded_by_contract"),
    ("gold", "quarantined"),
)


@dataclass(frozen=True, slots=True)
class PipelineRunAnchor:
    """Latest terminal run identity used to seed current-metric samples."""

    pipeline: str
    run_type: str
    status: str
    provider: str | None
    run_id: str


@dataclass(frozen=True, slots=True)
class RehydrateResult:
    """Outcome of one rehydrate pass."""

    anchors: int
    pipeline_runs_seeded: int
    provider_universe_seeded: int
    stage_series_seeded: int
    error: str | None = None


def reset_rehydrate_seed_state() -> None:
    """Clear process-local seed memory (tests only)."""
    _SEEDED_RUN_KEYS.clear()
    _SEEDED_PROVIDER_KEYS.clear()
    _SEEDED_STAGE_KEYS.clear()


def collect_latest_terminal_anchors(
    *,
    root: Path | None = None,
    limit: int = 200,
) -> tuple[PipelineRunAnchor, ...]:
    """Return one latest terminal anchor per pipeline × run_type × status."""
    entries = list_pipeline_reports(pipeline_name=None, limit=limit, root=root)
    selected: dict[tuple[str, str, str], PipelineRunAnchor] = {}
    for entry in entries:
        payload = _load_report_payload(entry.json_path)
        if payload is None:
            continue
        identity = payload.get("identity")
        if not isinstance(identity, dict):
            continue
        pipeline = str(identity.get("pipeline_name") or entry.owner or "").strip()
        run_type = str(identity.get("run_type") or "").strip()
        status = str(identity.get("status") or entry.status or "").strip()
        run_id = str(identity.get("run_id") or entry.run_id or "").strip()
        if not pipeline or not run_type or status not in _TERMINAL_STATUSES:
            continue
        key = (pipeline, run_type, status)
        if key in selected:
            continue
        provider_raw = identity.get("provider")
        provider = str(provider_raw).strip() if isinstance(provider_raw, str) else None
        selected[key] = PipelineRunAnchor(
            pipeline=pipeline,
            run_type=run_type,
            status=status,
            provider=provider or None,
            run_id=run_id,
        )
    return tuple(selected.values())


def rehydrate_current_pipeline_run_metrics(
    metrics: MetricsPort,
    *,
    root: Path | None = None,
) -> RehydrateResult:
    """Ensure scraped contract samples exist for latest terminal runs."""
    try:
        anchors = collect_latest_terminal_anchors(root=root)
        runs_seeded = 0
        providers_seeded = 0
        stages_seeded = 0
        for anchor in anchors:
            runs_seeded += _seed_pipeline_runs_total(metrics, anchor)
            providers_seeded += _seed_provider_universe(metrics, anchor)
            stages_seeded += _seed_stage_series(metrics, anchor)
        return RehydrateResult(
            anchors=len(anchors),
            pipeline_runs_seeded=runs_seeded,
            provider_universe_seeded=providers_seeded,
            stage_series_seeded=stages_seeded,
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


def rehydrate_current_metrics_safely(*, root: Path | None = None) -> RehydrateResult:
    """Best-effort rehydrate using the process Prometheus registry."""
    try:
        from bioetl.infrastructure.observability.prometheus_metrics import (
            PrometheusMetrics,
        )

        return rehydrate_current_pipeline_run_metrics(PrometheusMetrics(), root=root)
    except (
        ImportError,
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


def _seed_pipeline_runs_total(metrics: MetricsPort, anchor: PipelineRunAnchor) -> int:
    key = (anchor.pipeline, anchor.run_type, anchor.status)
    if key in _SEEDED_RUN_KEYS:
        return 0
    metrics.increment_counter(
        "bioetl_pipeline_runs_total",
        1,
        {
            "pipeline": anchor.pipeline,
            "run_type": anchor.run_type,
            "status": anchor.status,
        },
    )
    _SEEDED_RUN_KEYS.add(key)
    return 1


def _seed_provider_universe(metrics: MetricsPort, anchor: PipelineRunAnchor) -> int:
    provider = anchor.provider
    if provider is None or provider in _SEEDED_PROVIDER_KEYS:
        return 0
    metrics.increment_counter(
        "bioetl_health_check_success_total",
        1,
        {"provider": provider},
    )
    _SEEDED_PROVIDER_KEYS.add(provider)
    return 1


def _seed_stage_series(metrics: MetricsPort, anchor: PipelineRunAnchor) -> int:
    seeded = 0
    for stage, outcome in _STAGE_OUTCOMES:
        key = (anchor.pipeline, anchor.run_type, stage, outcome)
        if key in _SEEDED_STAGE_KEYS:
            continue
        metrics.increment_counter(
            "bioetl_stage_records_total",
            0,
            {
                "pipeline": anchor.pipeline,
                "run_type": anchor.run_type,
                "stage": stage,
                "outcome": outcome,
            },
        )
        metrics.increment_counter(
            "bioetl_records_processed_total",
            0,
            {
                "pipeline": anchor.pipeline,
                "stage": stage,
                "run_type": anchor.run_type,
            },
        )
        _SEEDED_STAGE_KEYS.add(key)
        seeded += 1
    return seeded


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
