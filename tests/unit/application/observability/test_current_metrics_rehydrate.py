"""OBS-FILL-01/02: rehydrate scraped current-metric samples from run reports."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.observability.current_metrics_rehydrate import (
    collect_latest_terminal_anchors,
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
