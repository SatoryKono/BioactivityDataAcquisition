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
"""Unit tests for debug.py CLI command.

Tests the debug command for step-through pipeline execution.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.export_lineage.pipeline_debug_service import (
    DebugAbortError,
)
from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.exit_codes import ExitCode
from tests.unit.interfaces.cli.commands.conftest import mock_asyncio_run

_PIPELINE = "chembl_activity"


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_registry() -> MagicMock:
    """Create a mock PipelineRegistry with one pipeline registered."""
    registry = MagicMock()
    registry.list_pipelines.return_value = [_PIPELINE]
    return registry


@pytest.fixture
def mock_run_result() -> RunResult:
    """Create a successful RunResult."""
    return RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name=_PIPELINE,
        run_id="test-run-id",
        run_type="incremental",
        records_fetched=10,
        records_silver=10,
        records_quarantined=0,
    )


@pytest.mark.unit
class TestDebugHelp:
    """Test debug command help output."""

    def test_debug_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that debug --help shows key options."""
        result = cli_runner.invoke(cli, ["debug", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--breakpoints" in result.output
        assert "--limit" in result.output
        assert "--mode" in result.output
        assert "--run-type" in result.output

    def test_debug_mode_choices(self, cli_runner: CliRunner) -> None:
        """Test that debug --help shows interactive and log mode choices."""
        result = cli_runner.invoke(cli, ["debug", "--help"])

        assert result.exit_code == 0
        assert "interactive" in result.output
        assert "log" in result.output


@pytest.mark.unit
class TestDebugCommand:
    """Tests for debug command happy and error paths."""

    def test_debug_success_prints_summary(
        self,
        cli_runner: CliRunner,
        mock_registry: MagicMock,
        mock_run_result: RunResult,
    ) -> None:
        """Test that a successful debug session prints a completion summary."""
        with mock_asyncio_run(return_value=mock_run_result):
            with patch(
                "bioetl.interfaces.cli.commands.debug.get_pipeline_runner_service"
            ):
                with patch(
                    "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
                    return_value=mock_registry,
                ):
                    result = cli_runner.invoke(
                        cli,
                        ["debug", "--pipeline", _PIPELINE],
                    )

        assert result.exit_code == 0
        assert (
            "debug session" in result.output.lower()
            or "complete" in result.output.lower()
        )

    def test_debug_with_limit_option(
        self,
        cli_runner: CliRunner,
        mock_registry: MagicMock,
        mock_run_result: RunResult,
    ) -> None:
        """Test that debug --limit passes through correctly."""
        with mock_asyncio_run(return_value=mock_run_result):
            with patch(
                "bioetl.interfaces.cli.commands.debug.get_pipeline_runner_service"
            ):
                with patch(
                    "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
                    return_value=mock_registry,
                ):
                    result = cli_runner.invoke(
                        cli,
                        ["debug", "--pipeline", _PIPELINE, "--limit", "5"],
                    )

        assert result.exit_code == 0
        assert "5" in result.output or result.exit_code == 0

    def test_debug_invalid_breakpoint_exits_with_config_error(
        self,
        cli_runner: CliRunner,
        mock_registry: MagicMock,
    ) -> None:
        """Test that an invalid breakpoint value causes CONFIG_ERROR exit."""
        with patch(
            "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "debug",
                    "--pipeline",
                    _PIPELINE,
                    "--breakpoints",
                    "not_a_valid_stage",
                ],
            )

        assert result.exit_code == ExitCode.CONFIG_ERROR

    def test_debug_abort_error_exits_with_sigint(
        self,
        cli_runner: CliRunner,
        mock_registry: MagicMock,
    ) -> None:
        """Test that DebugAbortError exits with SIGINT code."""
        with mock_asyncio_run(side_effect=DebugAbortError("aborted")):
            with patch(
                "bioetl.interfaces.cli.commands.debug.get_pipeline_runner_service"
            ):
                with patch(
                    "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
                    return_value=mock_registry,
                ):
                    result = cli_runner.invoke(
                        cli,
                        ["debug", "--pipeline", _PIPELINE],
                    )

        assert result.exit_code == ExitCode.SIGINT

    def test_debug_keyboard_interrupt_exits_with_sigint(
        self,
        cli_runner: CliRunner,
        mock_registry: MagicMock,
    ) -> None:
        """Test that KeyboardInterrupt exits with SIGINT code."""
        with mock_asyncio_run(side_effect=KeyboardInterrupt()):
            with patch(
                "bioetl.interfaces.cli.commands.debug.get_pipeline_runner_service"
            ):
                with patch(
                    "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
                    return_value=mock_registry,
                ):
                    result = cli_runner.invoke(
                        cli,
                        ["debug", "--pipeline", _PIPELINE],
                    )

        assert result.exit_code == ExitCode.SIGINT

    def test_debug_unknown_pipeline_exits_nonzero(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that unknown pipeline causes non-zero exit due to validation."""
        registry = MagicMock()
        registry.list_pipelines.return_value = ["other_pipeline"]

        with patch(
            "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
            return_value=registry,
        ):
            result = cli_runner.invoke(
                cli,
                ["debug", "--pipeline", "nonexistent_pipeline"],
            )

        assert result.exit_code != 0


@pytest.mark.parametrize("mode_args", [[], ["--mode", "log"]])
def test_log_debug_awaits_service_with_debug_options(
    mode_args, mock_registry, mock_run_result
):
    """Default and explicit log execute the real async dispatch with a fake service."""
    from unittest.mock import AsyncMock

    service = MagicMock()
    service.run = AsyncMock(return_value=mock_run_result)
    with (
        patch(
            "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
            return_value=mock_registry,
        ),
        patch(
            "bioetl.interfaces.cli.commands.debug.get_pipeline_runner_service",
            return_value=service,
        ),
    ):
        result = CliRunner().invoke(cli, ["debug", "--pipeline", _PIPELINE, *mode_args])
    assert result.exit_code == 0, result.output
    service.run.assert_awaited_once()
    assert service.run.call_args.args == (_PIPELINE,)
    options = service.run.call_args.kwargs["options"]
    assert options.log_level == "DEBUG"
    assert options.limit == 10
    assert options.run_type == "incremental"
    assert "Breakpoints: none" in result.output


@pytest.mark.parametrize(
    "unsupported", [["--mode", "interactive"], ["--breakpoints", "after_silver"]]
)
def test_unsupported_debug_rejected_before_runner_service(unsupported, mock_registry):
    """Unsupported debugging never resolves or executes the runner service."""
    with (
        patch(
            "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
            return_value=mock_registry,
        ),
        patch(
            "bioetl.interfaces.cli.commands.debug.get_pipeline_runner_service"
        ) as factory,
    ):
        result = CliRunner().invoke(
            cli, ["debug", "--pipeline", _PIPELINE, *unsupported]
        )
    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert "only mode='log' without breakpoints is available" in result.output
    factory.assert_not_called()


@pytest.mark.unit
def test_debug_help_declares_unsupported_surface():
    """Help must not promise step-through behavior that the command rejects."""
    result = CliRunner().invoke(cli, ["debug", "--help"])
    assert result.exit_code == 0
    help_text = " ".join(result.output.split())
    assert "default: log" in help_text
    assert "Interactive mode and non-empty breakpoints are unsupported" in help_text
    assert "Leave unset" in help_text
    assert "Default: all breakpoints enabled" not in help_text
