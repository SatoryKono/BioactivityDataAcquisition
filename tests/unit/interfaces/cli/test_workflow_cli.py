"""Unit tests for declarative workflow CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
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
) -> None:
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


def test_workflow_status_json_payload_includes_explicit_limits(
    cli_runner: CliRunner,
) -> None:
    result = cli_runner.invoke(
        cli,
        ["workflow", "status", "chembl_core", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"execution_history_available": false' in result.output.lower()
    assert '"history_scope": "bounded-static-config"' in result.output
