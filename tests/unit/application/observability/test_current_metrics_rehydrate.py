"""OBS-FILL-01/02: rehydrate scraped current-metric samples from run reports."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.observability.current_metrics_rehydrate import (
    collect_latest_terminal_anchors,
    collect_latest_terminal_workflow_anchors,
    rehydrate_current_pipeline_run_metrics,
    reset_rehydrate_seed_state,
)
from bioetl.application.observability.current_metrics_reconciliation import (
    reconcile_current_metrics_with_run_reports,
)

pytestmark = pytest.mark.unit


def _write_report(
    root: Path,
    *,
    pipeline: str,
    run_id: str,
    run_type: str,
    status: str,
    provider: str | None = "chembl",
) -> Path:
    run_dir = root / "pipeline" / pipeline / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "pipeline_run_report_v1",
        "identity": {
            "run_id": run_id,
            "pipeline_name": pipeline,
            "run_type": run_type,
            "status": status,
            "provider": provider,
        },
    }
    path = run_dir / "pipeline-run-report.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_collects_latest_terminal_anchor_per_pipeline_run_type_status(
    tmp_path: Path,
) -> None:
    _write_report(
        tmp_path,
        pipeline="chembl_assay",
        run_id="older",
        run_type="backfill",
        status="success",
    )
    _write_report(
        tmp_path,
        pipeline="chembl_assay",
        run_id="newer",
        run_type="backfill",
        status="success",
    )
    anchors = collect_latest_terminal_anchors(root=tmp_path, limit=20)
    assert len(anchors) == 1
    assert anchors[0].pipeline == "chembl_assay"
    assert anchors[0].run_type == "backfill"
    assert anchors[0].status == "success"
    assert anchors[0].provider == "chembl"


def test_rehydrate_increments_pipeline_runs_total_once(tmp_path: Path) -> None:
    reset_rehydrate_seed_state()
    _write_report(
        tmp_path,
        pipeline="chembl_assay",
        run_id="run-1",
        run_type="backfill",
        status="success",
    )
    metrics = MagicMock()
    first = rehydrate_current_pipeline_run_metrics(metrics, root=tmp_path)
    second = rehydrate_current_pipeline_run_metrics(metrics, root=tmp_path)

    assert first.pipeline_runs_seeded == 1
    assert second.pipeline_runs_seeded == 0
    metrics.set_gauge.assert_any_call(
        "bioetl_control_plane_manifest_present",
        1.0,
        {"pipeline": "chembl_assay", "run_type": "backfill"},
    )
    metrics.increment_counter.assert_called_once_with(
        "bioetl_pipeline_runs_total",
        0,
        {
            "pipeline": "chembl_assay",
            "run_type": "backfill",
            "status": "success",
        },
    )
    counter_names = [
        call.args[0] for call in metrics.increment_counter.call_args_list if call.args
    ]
    assert "bioetl_health_check_success_total" not in counter_names


def test_rehydrate_seeds_provider_universe_and_stage_series(tmp_path: Path) -> None:
    reset_rehydrate_seed_state()
    _write_report(
        tmp_path,
        pipeline="chembl_assay",
        run_id="run-1",
        run_type="backfill",
        status="success",
        provider="chembl",
    )
    metrics = MagicMock()
    result = rehydrate_current_pipeline_run_metrics(metrics, root=tmp_path)
    assert result.provider_universe_seeded == 1
    assert result.stage_series_seeded == 0
    metrics.set_gauge.assert_any_call(
        "bioetl_provider_observed_universe",
        1.0,
        {"provider": "chembl"},
    )
    counter_calls = [
        call.args for call in metrics.increment_counter.call_args_list if call.args
    ]
    assert counter_calls == [
        (
            "bioetl_pipeline_runs_total",
            0,
            {
                "pipeline": "chembl_assay",
                "run_type": "backfill",
                "status": "success",
            },
        )
    ]


def test_reconciliation_reports_gap_when_success_lacks_scrape_sample(
    tmp_path: Path,
) -> None:
    _write_report(
        tmp_path,
        pipeline="chembl_assay",
        run_id="run-1",
        run_type="backfill",
        status="success",
    )
    result = reconcile_current_metrics_with_run_reports(
        root=tmp_path,
        exposition="# HELP bioetl_pipeline_runs_total x\n# TYPE bioetl_pipeline_runs_total counter\n",
    )
    assert result.status == "unhealthy"
    assert result.state == "durable_success_without_scrape_samples"
    assert result.missing_pipelines == ("chembl_assay:backfill",)


def test_rehydrate_writes_scrape_sample_to_prometheus_registry(
    tmp_path: Path,
) -> None:
    reset_rehydrate_seed_state()
    _write_report(
        tmp_path,
        pipeline="obs_fill_rehydrate_probe",
        run_id="run-probe",
        run_type="backfill",
        status="success",
        provider="chembl",
    )
    from prometheus_client import REGISTRY, generate_latest

    from bioetl.infrastructure.observability.health_metrics_exposition import (
        build_health_server_metrics_exposition,
    )
    from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

    def _health_check_samples(body: str) -> list[str]:
        return [
            line
            for line in body.splitlines()
            if line.startswith("bioetl_health_check_success_total{")
        ]

    before_health = _health_check_samples(generate_latest(REGISTRY).decode("utf-8"))
    result = rehydrate_current_pipeline_run_metrics(PrometheusMetrics(), root=tmp_path)
    assert result.error is None
    assert result.pipeline_runs_seeded == 1
    body = build_health_server_metrics_exposition()
    assert "bioetl_provider_observed_universe" in body
    assert 'provider="chembl"' in body
    sample_lines = [
        line
        for line in body.splitlines()
        if line.startswith("bioetl_pipeline_runs_total{")
        and 'pipeline="obs_fill_rehydrate_probe"' in line
    ]
    assert len(sample_lines) == 1
    assert 'run_type="backfill"' in sample_lines[0]
    assert 'status="success"' in sample_lines[0]
    assert sample_lines[0].rsplit("}", 1)[-1].strip() in {"0", "0.0"}
    aligned = reconcile_current_metrics_with_run_reports(
        root=tmp_path,
        exposition=body,
    )
    assert aligned.status == "healthy"
    assert aligned.state == "aligned"
    assert _health_check_samples(body) == before_health


def test_reconciliation_aligned_when_labeled_sample_present(tmp_path: Path) -> None:
    _write_report(
        tmp_path,
        pipeline="chembl_assay",
        run_id="run-1",
        run_type="backfill",
        status="success",
    )
    exposition = (
        'bioetl_pipeline_runs_total{pipeline="chembl_assay",'
        'run_type="backfill",status="success"} 1.0\n'
    )
    result = reconcile_current_metrics_with_run_reports(
        root=tmp_path,
        exposition=exposition,
    )
    assert result.status == "healthy"
    assert result.state == "aligned"
    assert result.missing_pipelines == ()
    assert result.missing_workflows == ()


def _write_workflow_report(
    root: Path,
    *,
    workflow: str,
    run_id: str,
    status: str,
    pipelines: tuple[tuple[str, str], ...] = (),
    attach_children: bool = True,
) -> Path:
    run_dir = root / "workflow" / workflow / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    execution: list[dict[str, object]] = []
    plan_steps: list[dict[str, object]] = []
    for pipeline, child_run_id in pipelines:
        step_id = f"run_{pipeline}"
        plan_steps.append(
            {
                "step_id": step_id,
                "kind": "pipeline",
                "pipeline_name": pipeline,
            }
        )
        row: dict[str, object] = {
            "step_id": step_id,
            "kind": "pipeline",
            "pipeline_name": pipeline,
            "status": "success",
            "records_extracted": 1,
        }
        if attach_children:
            row["pipeline_run_id"] = child_run_id
            _write_report(
                root,
                pipeline=pipeline,
                run_id=child_run_id,
                run_type="backfill",
                status="success",
            )
        execution.append(row)
    payload = {
        "schema_version": "workflow_run_report_v1",
        "identity": {
            "workflow_run_id": run_id,
            "workflow_name": workflow,
            "status": status,
            "completed_at": "2026-09-06T11:22:53+00:00",
        },
        "plan": {"steps": plan_steps},
        "execution": execution,
        "totals": {
            "steps_planned": len(plan_steps),
            "steps_succeeded": len(execution),
            "steps_failed": 0,
            "steps_skipped": 0,
            "records_extracted_sum": len(execution),
        },
    }
    path = run_dir / "workflow-run-report.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_collects_latest_terminal_workflow_anchor_per_workflow(
    tmp_path: Path,
) -> None:
    _write_workflow_report(
        tmp_path,
        workflow="chembl_baseline",
        run_id="older",
        status="success",
        pipelines=(("chembl_assay", "assay-old"),),
    )
    _write_workflow_report(
        tmp_path,
        workflow="chembl_baseline",
        run_id="newer",
        status="success",
        pipelines=(("chembl_assay", "assay-new"),),
    )
    anchors = collect_latest_terminal_workflow_anchors(root=tmp_path, limit=20)
    chembl = [anchor for anchor in anchors if anchor.workflow == "chembl_baseline"]
    assert len(chembl) == 1
    assert chembl[0].status == "success"
    assert chembl[0].provider == "chembl"


def test_rehydrate_seeds_workflow_expected_once(tmp_path: Path) -> None:
    reset_rehydrate_seed_state()
    _write_workflow_report(
        tmp_path,
        workflow="chembl_baseline",
        run_id="wf-1",
        status="success",
        pipelines=(("chembl_assay", "assay-1"),),
    )
    metrics = MagicMock()
    first = rehydrate_current_pipeline_run_metrics(metrics, root=tmp_path)
    second = rehydrate_current_pipeline_run_metrics(metrics, root=tmp_path)

    assert first.workflow_expected_seeded == 1
    assert first.workflow_pipeline_expected_seeded == 1
    assert second.workflow_expected_seeded == 0
    metrics.set_gauge.assert_any_call(
        "bioetl_workflow_expected",
        1.0,
        {"workflow": "chembl_baseline", "provider": "chembl"},
    )
    metrics.set_gauge.assert_any_call(
        "bioetl_workflow_pipeline_expected",
        1.0,
        {
            "workflow": "chembl_baseline",
            "pipeline": "chembl_assay",
            "run_type": "backfill",
            "provider": "chembl",
        },
    )
    counter_names = [
        call.args[0] for call in metrics.increment_counter.call_args_list if call.args
    ]
    assert "bioetl_workflow_runs_total" not in counter_names


def test_reconciliation_reports_workflow_gap_when_success_lacks_scrape_sample(
    tmp_path: Path,
) -> None:
    _write_workflow_report(
        tmp_path,
        workflow="chembl_baseline",
        run_id="wf-1",
        status="success",
        pipelines=(("chembl_assay", "assay-1"),),
        attach_children=False,
    )
    result = reconcile_current_metrics_with_run_reports(
        root=tmp_path,
        exposition=(
            "# HELP bioetl_workflow_expected x\n# TYPE bioetl_workflow_expected gauge\n"
        ),
    )
    assert result.status == "unhealthy"
    assert result.state == "durable_workflow_success_without_scrape_samples"
    assert result.missing_workflows == ("chembl_baseline",)
    assert result.missing_pipelines == ()


def test_rehydrate_writes_workflow_expected_scrape_sample(
    tmp_path: Path,
) -> None:
    reset_rehydrate_seed_state()
    _write_workflow_report(
        tmp_path,
        workflow="obs_wf_sel_rehydrate_probe",
        run_id="wf-probe",
        status="success",
        pipelines=(("chembl_assay", "assay-probe"),),
    )
    from bioetl.infrastructure.observability.health_metrics_exposition import (
        build_health_server_metrics_exposition,
    )
    from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

    result = rehydrate_current_pipeline_run_metrics(PrometheusMetrics(), root=tmp_path)
    assert result.error is None
    assert result.workflow_expected_seeded == 1
    body = build_health_server_metrics_exposition()
    sample_lines = [
        line
        for line in body.splitlines()
        if line.startswith("bioetl_workflow_expected{")
        and 'workflow="obs_wf_sel_rehydrate_probe"' in line
    ]
    assert len(sample_lines) == 1
    assert 'provider="chembl"' in sample_lines[0]
    assert sample_lines[0].rsplit("}", 1)[-1].strip() in {"1", "1.0"}
    runs_total = [
        line
        for line in body.splitlines()
        if line.startswith("bioetl_workflow_runs_total{")
        and 'workflow="obs_wf_sel_rehydrate_probe"' in line
    ]
    assert runs_total == []
    aligned = reconcile_current_metrics_with_run_reports(
        root=tmp_path,
        exposition=body,
    )
    assert aligned.status == "healthy"
    assert aligned.state == "aligned"
    assert aligned.missing_workflows == ()
