"""Unit coverage for current-metrics rehydrate remaining below 75%."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.observability import current_metrics_rehydrate as subject
from bioetl.application.observability.current_metrics_rehydrate import (
    _anchor_from_report_entry,
    _persisted_unix,
    collect_latest_terminal_anchors,
    collect_latest_terminal_workflow_anchors,
    rehydrate_current_pipeline_run_metrics,
    reset_rehydrate_seed_state,
)
from bioetl.application.observability.rehydrate_models import (
    PipelineRunSnapshot,
    WorkflowPipelineScopeInfo,
    WorkflowRunSnapshot,
)
from bioetl.application.services.run_reports.query import ReportIndexEntry

pytestmark = pytest.mark.unit


def _file_run_report_store() -> object:
    from bioetl.infrastructure.storage.run_report_store_adapter import (
        FileRunReportStoreAdapter,
    )

    return FileRunReportStoreAdapter()


def _pipeline_report(
    root: Path,
    *,
    pipeline: str,
    run_id: str,
    status: str = "success",
    provider: str | None = "chembl",
    completed_at: str | None = "2026-01-01T00:00:00+00:00",
) -> Path:
    run_dir = root / "pipeline" / pipeline / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    identity: dict[str, object] = {
        "run_id": run_id,
        "pipeline_name": pipeline,
        "run_type": "backfill",
        "status": status,
    }
    if provider is not None:
        identity["provider"] = provider
    if completed_at is not None:
        identity["completed_at"] = completed_at
    path = run_dir / "pipeline-run-report.json"
    path.write_text(json.dumps({"identity": identity}), encoding="utf-8")
    return path


def _workflow_report(root: Path) -> Path:
    run_dir = root / "workflow" / "nightly" / "wf-1"
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "workflow-run-report.json"
    path.write_text(
        json.dumps(
            {
                "identity": {
                    "workflow_name": "nightly",
                    "status": "success",
                    "workflow_run_id": "wf-1",
                },
                "plan": {"steps": [{"pipeline_name": "chembl_assay"}]},
                "execution": [
                    {
                        "pipeline_name": "chembl_assay",
                        "run_type": "backfill",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_reset_and_persisted_unix() -> None:
    reset_rehydrate_seed_state()
    assert _persisted_unix("", 12.5) == 12.5
    assert _persisted_unix("not-iso", 9.0) == 9.0
    assert (
        _persisted_unix("2026-01-01T00:00:00+00:00", 0.0)
        == datetime(2026, 1, 1, tzinfo=UTC).timestamp()
    )


def test_anchor_rejects_invalid_payloads(tmp_path: Path) -> None:
    store = _file_run_report_store()
    missing = ReportIndexEntry(
        kind="pipeline",
        owner="chembl_assay",
        run_id="missing",
        json_path=tmp_path / "missing.json",
        markdown_path=None,
        status="success",
        started_at=None,
        completed_at=None,
        mtime=1.0,
    )
    assert _anchor_from_report_entry(missing, store=store) is None

    listed = tmp_path / "list.json"
    listed.write_text("[]", encoding="utf-8")
    listed_entry = replace(missing, json_path=listed, run_id="list")
    assert _anchor_from_report_entry(listed_entry, store=store) is None

    identity = tmp_path / "identity.json"
    identity.write_text(json.dumps({"identity": []}), encoding="utf-8")
    identity_entry = replace(missing, json_path=identity, run_id="identity")
    assert _anchor_from_report_entry(identity_entry, store=store) is None

    running = tmp_path / "running.json"
    running.write_text(
        json.dumps(
            {
                "identity": {
                    "pipeline_name": "chembl_assay",
                    "run_type": "backfill",
                    "status": "running",
                    "run_id": "r1",
                }
            }
        ),
        encoding="utf-8",
    )
    running_entry = replace(missing, json_path=running, run_id="r1", status="running")
    assert _anchor_from_report_entry(running_entry, store=store) is None


def test_collect_and_rehydrate(tmp_path: Path) -> None:
    reset_rehydrate_seed_state()
    store = _file_run_report_store()
    _pipeline_report(tmp_path, pipeline="chembl_assay", run_id="older")
    _pipeline_report(tmp_path, pipeline="chembl_assay", run_id="newer")
    _pipeline_report(
        tmp_path,
        pipeline="chembl_assay",
        run_id="failed",
        status="failed",
        completed_at="bad-ts",
        provider=None,
    )
    _workflow_report(tmp_path)
    anchors = collect_latest_terminal_anchors(root=tmp_path, limit=20, store=store)
    assert {item.status for item in anchors} == {"success", "failed"}
    workflows = collect_latest_terminal_workflow_anchors(
        root=tmp_path, limit=20, store=store
    )
    assert len(workflows) == 1
    metrics = MagicMock()
    first = rehydrate_current_pipeline_run_metrics(metrics, root=tmp_path, store=store)
    second = rehydrate_current_pipeline_run_metrics(metrics, root=tmp_path, store=store)
    assert first.pipeline_runs_seeded >= 1
    assert first.workflow_expected_seeded == 1
    assert first.workflow_pipeline_expected_seeded >= 1
    assert second.pipeline_runs_seeded == 0
    assert second.error is None


def test_rehydrate_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_rehydrate_seed_state()
    monkeypatch.setattr(
        subject,
        "collect_latest_terminal_anchors",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("store down")),
    )
    result = rehydrate_current_pipeline_run_metrics(MagicMock(), store=MagicMock())
    assert result.anchors == 0
    assert result.error == "store down"


def test_seed_helpers_skip_duplicates() -> None:
    reset_rehydrate_seed_state()
    metrics = MagicMock()
    none_provider = PipelineRunSnapshot(
        pipeline="chembl_assay",
        run_type="backfill",
        status="success",
        provider=None,
        run_id="r1",
        observed_unix=1.0,
    )
    assert subject._seed_pipeline_runs_total(metrics, none_provider) == 1
    assert subject._seed_pipeline_runs_total(metrics, none_provider) == 0
    assert subject._seed_provider_universe(metrics, none_provider) == 0
    with_provider = PipelineRunSnapshot(
        pipeline="chembl_assay",
        run_type="backfill",
        status="success",
        provider="chembl",
        run_id="r1",
        observed_unix=1.0,
    )
    assert subject._seed_provider_universe(metrics, with_provider) == 1
    assert subject._seed_provider_universe(metrics, with_provider) == 0
    assert subject._seed_stage_series(metrics, with_provider) == 0
    workflow = WorkflowRunSnapshot(
        workflow="nightly",
        status="success",
        provider="chembl",
        run_id="wf-1",
        pipelines=(
            WorkflowPipelineScopeInfo(
                pipeline="chembl_assay", run_type="backfill", provider="chembl"
            ),
        ),
    )
    assert subject._seed_workflow_expected(metrics, workflow) == 1
    assert subject._seed_workflow_expected(metrics, workflow) == 0
    assert subject._seed_workflow_pipeline_expected(metrics, workflow) == 1
    assert subject._seed_workflow_pipeline_expected(metrics, workflow) == 0
