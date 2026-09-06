"""Compare durable exact-run success with scraped current-metric presence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bioetl.application.observability.current_metrics_rehydrate import (
    collect_latest_terminal_anchors,
    collect_latest_terminal_workflow_anchors,
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
    durable_workflow_success_count: int = 0
    scrape_has_workflow_expected: bool = False
    missing_workflows: tuple[str, ...] = ()


def reconcile_current_metrics_with_run_reports(
    *,
    root: Path | None = None,
    exposition: str | None = None,
) -> CurrentMetricsReconciliationOutcome:
    """Return an explicit gap reason when durable success lacks scrape samples."""
    anchors = collect_latest_terminal_anchors(root=root)
    workflow_anchors = collect_latest_terminal_workflow_anchors(root=root)
    successes = tuple(anchor for anchor in anchors if anchor.status == "success")
    workflow_successes = tuple(
        anchor for anchor in workflow_anchors if anchor.status == "success"
    )
    body = exposition if exposition is not None else ""
    scrape_has_samples = _exposition_has_pipeline_runs_sample(body)
    scrape_has_workflow = _exposition_has_workflow_expected_sample(body)
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
    missing_workflows = tuple(
        sorted(
            {
                anchor.workflow
                for anchor in workflow_successes
                if not _exposition_has_labeled_workflow_expected_sample(
                    body,
                    workflow=anchor.workflow,
                )
            }
        )
    )
    return _reconcile_outcome(
        successes=successes,
        workflow_successes=workflow_successes,
        scrape_has_samples=scrape_has_samples,
        scrape_has_workflow=scrape_has_workflow,
        missing=missing,
        missing_workflows=missing_workflows,
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
        "durable_workflow_success_count": result.durable_workflow_success_count,
        "scrape_has_workflow_expected": result.scrape_has_workflow_expected,
        "missing_workflows": list(result.missing_workflows),
    }


def _reconcile_outcome(
    *,
    successes: tuple[object, ...],
    workflow_successes: tuple[object, ...],
    scrape_has_samples: bool,
    scrape_has_workflow: bool,
    missing: tuple[str, ...],
    missing_workflows: tuple[str, ...],
) -> CurrentMetricsReconciliationOutcome:
    if not successes and not workflow_successes:
        return CurrentMetricsReconciliationOutcome(
            status="healthy",
            state="no_durable_success",
            message=(
                "No terminal success reports found; current-metrics gap is "
                "not contradicted by exact-run HTTP."
            ),
            durable_success_count=0,
            scrape_has_pipeline_runs_total=scrape_has_samples,
            missing_pipelines=(),
            scrape_has_workflow_expected=scrape_has_workflow,
        )
    if missing or missing_workflows:
        return CurrentMetricsReconciliationOutcome(
            status="unhealthy",
            state=_gap_state(missing=missing),
            message=_gap_message(missing=missing, missing_workflows=missing_workflows),
            durable_success_count=len(successes),
            scrape_has_pipeline_runs_total=scrape_has_samples,
            missing_pipelines=missing,
            durable_workflow_success_count=len(workflow_successes),
            scrape_has_workflow_expected=scrape_has_workflow,
            missing_workflows=missing_workflows,
        )
    return CurrentMetricsReconciliationOutcome(
        status="healthy",
        state="aligned",
        message=_aligned_message(
            has_pipelines=bool(successes),
            has_workflows=bool(workflow_successes),
        ),
        durable_success_count=len(successes),
        scrape_has_pipeline_runs_total=bool(successes) or scrape_has_samples,
        missing_pipelines=(),
        durable_workflow_success_count=len(workflow_successes),
        scrape_has_workflow_expected=True
        if workflow_successes
        else scrape_has_workflow,
        missing_workflows=(),
    )


def _gap_state(*, missing: tuple[str, ...]) -> str:
    if missing:
        return "durable_success_without_scrape_samples"
    return "durable_workflow_success_without_scrape_samples"


def _gap_message(
    *, missing: tuple[str, ...], missing_workflows: tuple[str, ...]
) -> str:
    parts: list[str] = []
    if missing:
        parts.append(
            "Exact-run reports show success but scraped "
            "bioetl_pipeline_runs_total samples are missing for "
            + ", ".join(missing)
            + "."
        )
    if missing_workflows:
        parts.append(
            "Durable workflow reports show success but scraped "
            "bioetl_workflow_expected samples are missing for "
            + ", ".join(missing_workflows)
            + "."
        )
    return " ".join(parts)


def _aligned_message(*, has_pipelines: bool, has_workflows: bool) -> str:
    if has_pipelines and has_workflows:
        return (
            "Durable success reports have matching scraped "
            "bioetl_pipeline_runs_total and bioetl_workflow_expected samples."
        )
    if has_workflows:
        return (
            "Durable workflow success reports have matching scraped "
            "bioetl_workflow_expected samples."
        )
    return "Durable success reports have matching scraped bioetl_pipeline_runs_total samples."


def _exposition_has_pipeline_runs_sample(body: str) -> bool:
    for line in body.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("bioetl_pipeline_runs_total"):
            return True
    return False


def _exposition_has_workflow_expected_sample(body: str) -> bool:
    for line in body.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("bioetl_workflow_expected"):
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


def _exposition_has_labeled_workflow_expected_sample(
    body: str,
    *,
    workflow: str,
) -> bool:
    needle = f'workflow="{workflow}"'
    for line in body.splitlines():
        if not line.startswith("bioetl_workflow_expected{"):
            continue
        if needle in line:
            return True
    return False
