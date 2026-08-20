"""Compare durable exact-run success with scraped current-metric presence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bioetl.application.observability.current_metrics_rehydrate import (
    collect_latest_terminal_anchors,
)


@dataclass(frozen=True, slots=True)
class CurrentMetricsReconciliationOutcome:
    """Operator-facing reconciliation of Ops HTTP success vs scrape samples."""

    status: str
    state: str
    message: str
    durable_success_count: int
    scrape_has_pipeline_runs_total: bool
    missing_pipelines: tuple[str, ...]


def reconcile_current_metrics_with_run_reports(
    *,
    root: Path | None = None,
    exposition: str | None = None,
) -> CurrentMetricsReconciliationOutcome:
    """Return an explicit gap reason when durable success lacks scrape samples."""
    anchors = collect_latest_terminal_anchors(root=root)
    successes = tuple(anchor for anchor in anchors if anchor.status == "success")
    body = exposition if exposition is not None else ""
    scrape_has_samples = _exposition_has_pipeline_runs_sample(body)
    missing = tuple(
        sorted(
            {
                f"{anchor.pipeline}:{anchor.run_type}"
                for anchor in successes
                if not _exposition_has_labeled_pipeline_runs_sample(
                    body,
                    pipeline=anchor.pipeline,
                    run_type=anchor.run_type,
                )
            }
        )
    )
    if not successes:
        return CurrentMetricsReconciliationOutcome(
            status="healthy",
            state="no_durable_success",
            message="No terminal success reports found; current-metrics gap is not contradicted by exact-run HTTP.",
            durable_success_count=0,
            scrape_has_pipeline_runs_total=scrape_has_samples,
            missing_pipelines=(),
        )
    if missing:
        return CurrentMetricsReconciliationOutcome(
            status="unhealthy",
            state="durable_success_without_scrape_samples",
            message=(
                "Exact-run reports show success but scraped "
                "bioetl_pipeline_runs_total samples are missing for "
                + ", ".join(missing)
                + "."
            ),
            durable_success_count=len(successes),
            scrape_has_pipeline_runs_total=scrape_has_samples,
            missing_pipelines=missing,
        )
    return CurrentMetricsReconciliationOutcome(
        status="healthy",
        state="aligned",
        message="Durable success reports have matching scraped bioetl_pipeline_runs_total samples.",
        durable_success_count=len(successes),
        scrape_has_pipeline_runs_total=True,
        missing_pipelines=(),
    )


def current_metrics_reconciliation_check(
    *,
    root: Path | None = None,
    exposition: str | None = None,
) -> dict[str, object]:
    """JSON payload for ``/health/ready`` (diagnostic; does not fail ready)."""
    result = reconcile_current_metrics_with_run_reports(
        root=root,
        exposition=exposition,
    )
    return {
        "status": result.status,
        "state": result.state,
        "message": result.message,
        "durable_success_count": result.durable_success_count,
        "scrape_has_pipeline_runs_total": result.scrape_has_pipeline_runs_total,
        "missing_pipelines": list(result.missing_pipelines),
    }


def _exposition_has_pipeline_runs_sample(body: str) -> bool:
    for line in body.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("bioetl_pipeline_runs_total"):
            return True
    return False


def _exposition_has_labeled_pipeline_runs_sample(
    body: str,
    *,
    pipeline: str,
    run_type: str,
) -> bool:
    needle_pipeline = f'pipeline="{pipeline}"'
    needle_run_type = f'run_type="{run_type}"'
    for line in body.splitlines():
        if not line.startswith("bioetl_pipeline_runs_total{"):
            continue
        if needle_pipeline in line and needle_run_type in line:
            return True
    return False
