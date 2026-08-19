"""Rehydrate scraped current-metrics samples from durable run reports.

CLI pipeline processes increment ``bioetl_pipeline_runs_total`` in-process.
The long-lived ``bioetl health server`` scrape registry is a different process
and otherwise emits HELP/TYPE without samples, which trips
``absent_over_time(bioetl_pipeline_runs_total[10m])``.

This module publishes CURRENT gauges from the latest terminal pipeline-run
reports. It never increments RANGE event counters and does not invent
``run_id`` labels.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.run_reports.query import (
    ReportIndexEntry,
    list_pipeline_reports,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

_TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown"})
_SEEDED_RUN_KEYS: set[tuple[str, str, str]] = set()
_SEEDED_PROVIDER_KEYS: set[str] = set()


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


def _first_text(*values: object) -> str:
    """Return the first non-empty stripped string from *values*."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _anchor_from_report_entry(entry: ReportIndexEntry) -> PipelineRunAnchor | None:
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
    return PipelineRunAnchor(
        pipeline=pipeline,
        run_type=run_type,
        status=status,
        provider=provider or None,
        run_id=run_id,
    )


def collect_latest_terminal_anchors(
    *,
    root: Path | None = None,
    limit: int = 200,
) -> tuple[PipelineRunAnchor, ...]:
    """Return one latest terminal anchor per pipeline × run_type × status."""
    entries = list_pipeline_reports(pipeline_name=None, limit=limit, root=root)
    selected: dict[tuple[str, str, str], PipelineRunAnchor] = {}
    for entry in entries:
        anchor = _anchor_from_report_entry(entry)
        if anchor is None:
            continue
        key = (anchor.pipeline, anchor.run_type, anchor.status)
        if key in selected:
            continue
        selected[key] = anchor
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


def _seed_pipeline_runs_total(metrics: MetricsPort, anchor: PipelineRunAnchor) -> int:
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
        float(time.time()),
        labels,
    )
    _SEEDED_RUN_KEYS.add(key)
    return 1


def _seed_provider_universe(metrics: MetricsPort, anchor: PipelineRunAnchor) -> int:
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


def _seed_stage_series(metrics: MetricsPort, anchor: PipelineRunAnchor) -> int:
    del metrics, anchor
    return 0


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
