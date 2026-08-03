# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for workflow CLI command surfaces."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig
from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def test_workflow_run_help_includes_observability_backend_options(
    cli_runner: CliRunner,
) -> None:
    result = cli_runner.invoke(cli, ["workflow", "run", "--help"])

    assert result.exit_code == 0
    assert "--ensure-observability-backend" in result.output
    assert "--observability-backend-port" in result.output
    assert "--debug-export / --no-debug-export" in result.output
    assert "--debug-export-format" in result.output
    assert "--debug-export-dir" in result.output


def test_workflow_run_ensures_observability_backend_before_execution(
    cli_runner: CliRunner,
) -> None:
    config = WorkflowConfig(
        name="chembl_publication",
        steps=(
            WorkflowStepConfig(
                step_id="run_chembl_publication",
                pipeline_name="chembl_publication",
            ),
        ),
    )
    result_payload = MagicMock(status="success")

    with (
        patch(
            "bioetl.interfaces.cli.commands.workflow._load_and_apply_workflow_config",
            return_value=config,
        ),
        patch(
            "bioetl.interfaces.cli.commands._workflow_command_runtime.ensure_observability_backend_started",
            return_value=ObservabilityBackendEnsureResult(
                status="started",
                health_url="http://127.0.0.1:8081/health",
            ),
        ) as ensure_backend,
        patch(
            "bioetl.interfaces.cli.commands._workflow_command_runtime._execute_workflow_and_publish_metrics",
            return_value=result_payload,
        ) as execute_workflow,
        patch(
            "bioetl.interfaces.cli.commands._workflow_command_runtime.render_run_result"
        ),
        patch(
            "bioetl.interfaces.cli.commands._workflow_command_runtime._handle_workflow_result"
        ),
    ):
        result = cli_runner.invoke(
            cli,
            [
                "workflow",
                "run",
                "chembl_publication",
                "--limit",
                "1",
            ],
        )

    assert result.exit_code == 0
    ensure_backend.assert_called_once_with(
        enabled=True,
        port=8081,
        required_probe_paths=("/ops/control-plane/ready",),
    )
    execute_workflow.assert_called_once()
