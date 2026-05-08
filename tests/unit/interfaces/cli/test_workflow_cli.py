"""Unit tests for declarative workflow CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from bioetl.application.services.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.interfaces.cli.main import cli


@dataclass
class _FakeWorkflowRunnerService:
    received_config: object | None = None

    async def run_workflow(
        self,
        config: object,
        **_: object,
    ) -> WorkflowRunExecutionResult:
        self.received_config = config
        return WorkflowRunExecutionResult(
            workflow_name="chembl_core",
            status="success",
            steps=(
                WorkflowStepExecutionResult(
                    step_id="chembl_activity_ingest",
                    step_kind="pipeline",
                    status="success",
                ),
                WorkflowStepExecutionResult(
                    step_id="chembl_assay_ingest",
                    step_kind="pipeline",
                    status="success",
                ),
                WorkflowStepExecutionResult(
                    step_id="summarize_core_extracts",
                    step_kind="transform",
                    status="success",
                ),
            ),
            workflow_run_id="00000000-0000-0000-0000-000000000111",
            manifest_id="manifest-111",
            execution_fingerprint="fingerprint-111",
        )


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def test_workflow_help_lists_run_and_status(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["workflow", "--help"])

    assert result.exit_code == 0
    assert "run" in result.output
    assert "status" in result.output


def test_workflow_status_is_bounded_and_step_oriented(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    class _NoHistoryInspectionService:
        def inspect_latest(self, _name: str) -> None:
            return None

    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_inspection_service",
        lambda: _NoHistoryInspectionService(),
        raising=True,
    )

    result = cli_runner.invoke(cli, ["workflow", "status", "chembl_core"])

    assert result.exit_code == 0
    assert "Workflow Status / chembl_core" in result.output
    assert "history: unavailable" in result.output
    assert "chembl_activity_ingest [pipeline]" in result.output
    assert "summarize_core_extracts [transform]" in result.output


def test_workflow_run_dry_run_smoke_uses_canonical_example_without_network(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_core",
            "--dry-run",
            "--only-steps",
            "summarize_core_extracts",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Workflow: chembl_core" in result.output
    assert "Workflow run ID: 00000000-0000-0000-0000-000000000111" in result.output
    assert fake_service.received_config is not None
    config = fake_service.received_config
    step_ids = tuple(getattr(step, "step_id") for step in getattr(config, "steps"))
    assert step_ids == (
        "chembl_activity_ingest",
        "chembl_assay_ingest",
        "summarize_core_extracts",
    )
    pipeline_steps = [
        step
        for step in getattr(config, "steps")
        if getattr(step, "pipeline_name", None) is not None
    ]
    assert all(
        getattr(step.run_options, "dry_run", None) is True for step in pipeline_steps
    )


def test_workflow_run_accepts_pipeline_style_runtime_overrides(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    input_csv = tmp_path / "ids.csv"
    input_csv.write_text("id\nCHEMBL1\n", encoding="utf-8")
    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_core",
            "--limit",
            "1000",
            "--start-offset",
            "5",
            "--input-csv",
            str(input_csv),
            "--filter-column",
            "molecule_id",
            "--filter-field",
            "molecule_chembl_id",
            "--vacuum-after-run",
            "--vacuum-retention-days",
            "7",
            "--log-level",
            "DEBUG",
            "--ignore-yaml-filter",
            "--skip-gold",
            "--execution-context",
            "shared",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
            "--cached-bronze-date",
            "2026-05-08",
            "--exact-replay",
            "--replay-of-run-id",
            "run-parent-1",
            "--replay-of-manifest-id",
            "manifest-parent-1",
            "--tracing",
        ],
    )

    assert result.exit_code == 0, result.output
    assert fake_service.received_config is not None
    config = fake_service.received_config
    pipeline_steps = [
        step
        for step in getattr(config, "steps")
        if getattr(step, "pipeline_name", None) is not None
    ]
    assert pipeline_steps
    assert all(
        getattr(step.run_options, "limit", None) == 1000 for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "start_offset", None) == 5 for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "input_csv", None) == str(input_csv)
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "filter_column", None) == "molecule_id"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "filter_field", None) == "molecule_chembl_id"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "vacuum_after_run", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "vacuum_retention_days", None) == 7
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "log_level", None) == "DEBUG"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "ignore_yaml_filter", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "skip_gold", None) is True for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "execution_context", None) == "shared"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "use_cached_bronze", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "cached_bronze_path", None) == str(cached_bronze_path)
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "cached_bronze_date", None) == "2026-05-08"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "exact_replay", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "replay_of_run_id", None) == "run-parent-1"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "replay_of_manifest_id", None) == "manifest-parent-1"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "enable_tracing", None) is True
        for step in pipeline_steps
    )


def test_workflow_run_starts_metrics_server_and_publishes_metrics(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    started_calls: list[bool] = []
    published_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "ensure_metrics_server_started",
        lambda: started_calls.append(True) or True,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "publish_metrics_safely",
        lambda **kwargs: published_calls.append(kwargs) or True,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        ["workflow", "run", "chembl_activity", "--limit", "5"],
    )

    assert result.exit_code == 0, result.output
    assert started_calls == [True]
    assert published_calls == [
        {
            "run_label": "bioetl",
            "pipeline_name": "chembl_activity",
            "run_type": "backfill",
            "grouping_key_extra": {
                "workflow_run_id": "00000000-0000-0000-0000-000000000111"
            },
        }
    ]


def test_workflow_run_publishes_metrics_even_when_workflow_fails(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd
    from bioetl.interfaces.cli.exit_codes import ExitCode

    class _FailingWorkflowExecutionService:
        async def run_workflow(
            self,
            config: object,
            **_: object,
        ) -> WorkflowRunExecutionResult:
            return WorkflowRunExecutionResult(
                workflow_name=getattr(config, "name", "chembl_activity"),
                status="failed",
                steps=(
                    WorkflowStepExecutionResult(
                        step_id="run_chembl_activity",
                        step_kind="pipeline",
                        status="failed",
                        error_type="RuntimeError",
                        error_message="boom",
                    ),
                ),
                workflow_run_id="00000000-0000-0000-0000-000000000222",
                manifest_id="manifest-222",
                execution_fingerprint="fingerprint-222",
            )

    published_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: _FailingWorkflowExecutionService(),
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "ensure_metrics_server_started",
        lambda: True,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "publish_metrics_safely",
        lambda **kwargs: published_calls.append(kwargs) or True,
        raising=True,
    )

    result = cli_runner.invoke(cli, ["workflow", "run", "chembl_activity"])

    assert result.exit_code == ExitCode.PIPELINE_ERROR
    assert published_calls == [
        {
            "run_label": "bioetl",
            "pipeline_name": "chembl_activity",
            "run_type": "backfill",
            "grouping_key_extra": {
                "workflow_run_id": "00000000-0000-0000-0000-000000000222"
            },
        }
    ]


def test_workflow_status_json_payload_includes_explicit_limits(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    class _NoHistoryInspectionService:
        def inspect_latest(self, _name: str) -> None:
            return None

    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_inspection_service",
        lambda: _NoHistoryInspectionService(),
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        ["workflow", "status", "chembl_core", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"execution_history_available": false' in result.output.lower()
    assert '"history_scope": "bounded-static-config"' in result.output
