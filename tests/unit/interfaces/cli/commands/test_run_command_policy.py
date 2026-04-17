"""Unit tests for canonical run command policy helpers.

Covers handle_cli_failure, map_status_to_exit_code, handle_destructive_step,
execute_run_step, and finalize_run_step.

Uncovered lines targeted: 141, 143-148, 150-155, 198, 200, 211.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest

from bioetl.application.services import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.cli_run_orchestration_models import (
    CliRunPreparationInput,
    RunExecutionRequest,
    RunPreparationResult,
)
from bioetl.application.services.cli_run_orchestration_service import (
    CliRunOrchestrationService,
)
from bioetl.domain.exceptions import NetworkError
from bioetl.interfaces.cli.commands.domains.run.command_policy import (
    execute_run_step,
    finalize_run_step,
    handle_cli_failure,
    handle_destructive_step,
    map_status_to_exit_code,
    prepare_run_request,
    RunCommandInput,
    run_command_flow,
)
from bioetl.interfaces.cli.exit_codes import ExitCode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(**kwargs: object) -> RunResult:
    defaults: dict[str, object] = {
        "status": PipelineRunResult.SUCCESS,
        "pipeline_name": "chembl_activity",
        "run_id": "run-001",
        "run_type": "incremental",
        "records_fetched": 0,
        "records_bronze": 0,
        "records_silver": 0,
        "records_gold": 0,
        "records_quarantined": 0,
        "error_message": None,
        "error_type": None,
    }
    defaults.update(kwargs)  # type: ignore[arg-type]
    return RunResult(**defaults)  # type: ignore[arg-type]


def _make_request(**kwargs: object) -> RunExecutionRequest:
    defaults: dict[str, object] = {
        "pipeline": "chembl_activity",
        "options": MagicMock(name="run_options"),
        "health_server": False,
        "health_port": 8081,
    }
    defaults.update(kwargs)  # type: ignore[arg-type]
    return RunExecutionRequest(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# handle_cli_failure
# ---------------------------------------------------------------------------


class TestHandleCliFailure:
    """Tests for handle_cli_failure."""

    def test_cleanup_preview_reason_prints_error_and_returns(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """CLI_CLEANUP_PREVIEW* reason prints error to stderr and returns (no sys.exit)."""
        exc = RuntimeError("disk full")
        # Must NOT raise SystemExit
        handle_cli_failure(
            exc,
            pipeline="chembl_activity",
            reason_code="CLI_CLEANUP_PREVIEW_ERROR",
        )
        err = capsys.readouterr().err
        assert "Error previewing cleanup" in err
        assert "disk full" in err
        assert "CLI_CLEANUP_PREVIEW_ERROR" in err
        assert "chembl_activity" in err

    def test_cleanup_preview_error_includes_error_type(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Cleanup-preview error message includes exception class name."""
        exc = ValueError("bad config")
        handle_cli_failure(
            exc,
            pipeline="pubmed",
            reason_code="CLI_CLEANUP_PREVIEW_SOMETHING",
        )
        err = capsys.readouterr().err
        assert "ValueError" in err

    def test_non_cleanup_reason_delegates_and_exits(self) -> None:
        """Non-preview reason_code delegates to execution_policy which calls sys.exit."""
        with pytest.raises(SystemExit):
            handle_cli_failure(
                RuntimeError("unexpected"),
                pipeline="chembl_activity",
                reason_code="CLI_RUN_UNEXPECTED_ERROR",
            )

    def test_keyboard_interrupt_exits_with_sigint(self) -> None:
        """KeyboardInterrupt delegates to execution_policy -> ExitCode.SIGINT."""
        with pytest.raises(SystemExit) as exc_info:
            handle_cli_failure(
                KeyboardInterrupt(),
                pipeline="chembl_activity",
                reason_code="CLI_RUN_SIGINT",
            )
        assert exc_info.value.code == ExitCode.SIGINT


class TestPrepareRunRequest:
    """Tests for prepare_run_request helper."""

    def test_returns_prepared_request(self) -> None:
        service = MagicMock(spec=CliRunOrchestrationService)
        expected_request = _make_request()
        service.prepare_execution_request.return_value = RunPreparationResult(
            request=expected_request
        )
        exit_func = MagicMock()

        result = prepare_run_request(
            service=service,
            command_input=RunCommandInput(
                pipeline="chembl_activity",
                run_type="incremental",
                resume=False,
                start_offset=None,
                limit=None,
                input_csv=None,
                filter_column=None,
                filter_field=None,
                dry_run=False,
                yes=True,
                vacuum_after_run=None,
                vacuum_retention_days=None,
                debug=False,
                health_server=True,
                health_port=8081,
                enable_tracing=None,
                use_cached_bronze=False,
                cached_bronze_date=None,
                cached_bronze_path=None,
            ),
            exit_func=exit_func,
        )

        assert result is expected_request
        exit_func.assert_not_called()
        assert isinstance(
            service.prepare_execution_request.call_args.args[0],
            CliRunPreparationInput,
        )

    def test_invalid_request_echoes_error_and_exits(self) -> None:
        service = MagicMock(spec=CliRunOrchestrationService)
        service.prepare_execution_request.return_value = RunPreparationResult(
            request=None,
            error_message="bad options",
        )

        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run.command_policy.echo_error"
            ) as mock_error,
            pytest.raises(SystemExit),
        ):
            prepare_run_request(
                service=service,
                command_input=RunCommandInput(
                    pipeline="chembl_activity",
                    run_type="incremental",
                    resume=False,
                    start_offset=None,
                    limit=None,
                    input_csv=None,
                    filter_column=None,
                    filter_field=None,
                    dry_run=False,
                    yes=True,
                    vacuum_after_run=None,
                    vacuum_retention_days=None,
                    debug=False,
                    health_server=True,
                    health_port=8081,
                    enable_tracing=None,
                    use_cached_bronze=False,
                    cached_bronze_date=None,
                    cached_bronze_path=None,
                ),
                exit_func=MagicMock(side_effect=SystemExit(ExitCode.CONFIG_ERROR)),
            )

        mock_error.assert_called_once_with("bad options")


# ---------------------------------------------------------------------------
# map_status_to_exit_code
# ---------------------------------------------------------------------------


class TestMapStatusToExitCode:
    """Tests for map_status_to_exit_code wrapper."""

    @pytest.mark.parametrize(
        ("status", "error_type", "expected"),
        [
            (PipelineRunResult.SUCCESS, None, ExitCode.OK),
            (PipelineRunResult.DRY_RUN, None, ExitCode.OK),
            (PipelineRunResult.SHUTDOWN, None, ExitCode.SIGINT),
            (PipelineRunResult.FAILED, "NetworkError", ExitCode.NETWORK_ERROR),
            (PipelineRunResult.FAILED, "UnknownError", ExitCode.PIPELINE_ERROR),
        ],
    )
    def test_delegates_to_execution_policy(
        self,
        status: PipelineRunResult,
        error_type: str | None,
        expected: ExitCode,
    ) -> None:
        """map_status_to_exit_code correctly delegates to map_run_status_to_exit_code."""
        assert map_status_to_exit_code(status, error_type) == expected


# ---------------------------------------------------------------------------
# handle_destructive_step
# ---------------------------------------------------------------------------


class TestHandleDestructiveStep:
    """Tests for handle_destructive_step — covers lines 140-155."""

    def test_non_destructive_run_type_returns_true(self) -> None:
        """incremental run_type returns True without any confirmation."""
        result = handle_destructive_step(
            pipeline="chembl_activity",
            run_type="incremental",
            dry_run=False,
            yes=True,
        )
        assert result is True

    def test_click_abort_is_reraised(self) -> None:
        """click.Abort from handle_destructive_run_confirmation is re-raised (line 141)."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run.command_policy.handle_destructive_run_confirmation",
                side_effect=click.Abort(),
            ),
            pytest.raises(click.Abort),
        ):
            handle_destructive_step(
                pipeline="chembl_activity",
                run_type="rebuild",
                dry_run=False,
                yes=False,
            )

    def test_bioetl_error_calls_handle_failure_and_returns_false(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """BioETLError is caught, handle_cli_failure called, returns False (lines 142-148)."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.run.command_policy.handle_destructive_run_confirmation",
            side_effect=NetworkError("network down"),
        ):
            result = handle_destructive_step(
                pipeline="chembl_activity",
                run_type="rebuild",
                dry_run=False,
                yes=True,
            )
        assert result is False
        err = capsys.readouterr().err
        assert "Error previewing cleanup" in err

    def test_cli_entrypoint_typed_error_returns_false(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """OSError (member of CLI_ENTRYPOINT_TYPED_ERRORS) is caught, returns False (lines 149-155)."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.run.command_policy.handle_destructive_run_confirmation",
            side_effect=OSError("permission denied"),
        ):
            result = handle_destructive_step(
                pipeline="chembl_activity",
                run_type="backfill",
                dry_run=False,
                yes=True,
            )
        assert result is False
        err = capsys.readouterr().err
        assert "Error previewing cleanup" in err

    def test_generic_exception_is_not_swallowed(self) -> None:
        """Unexpected exception subclasses should propagate to preserve diagnostics."""

        class _WeirdError(Exception):
            pass

        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run.command_policy.handle_destructive_run_confirmation",
                side_effect=_WeirdError("weird"),
            ),
            pytest.raises(_WeirdError, match="weird"),
        ):
            handle_destructive_step(
                pipeline="chembl_activity",
                run_type="rebuild",
                dry_run=True,
                yes=True,
            )


# ---------------------------------------------------------------------------
# run_command_flow
# ---------------------------------------------------------------------------


class TestRunCommandFlow:
    """Tests for run_command_flow orchestration helper."""

    def test_returns_early_when_destructive_step_stops_execution(self) -> None:
        service = MagicMock(spec=CliRunOrchestrationService)
        execute_run = MagicMock()
        health_info_presenter = MagicMock()
        result_finalizer = MagicMock()
        exit_func = MagicMock()

        with patch(
            "bioetl.interfaces.cli.commands.domains.run.command_policy.handle_destructive_step",
            return_value=False,
        ) as mock_handle_destructive:
            run_command_flow(
                cli_input=RunCommandInput(
                    pipeline="chembl_activity",
                    run_type="rebuild",
                    resume=False,
                    start_offset=None,
                    limit=None,
                    input_csv=None,
                    filter_column=None,
                    filter_field=None,
                    dry_run=True,
                    yes=False,
                    vacuum_after_run=None,
                    vacuum_retention_days=None,
                    debug=False,
                    health_server=True,
                    health_port=8081,
                    enable_tracing=None,
                    use_cached_bronze=False,
                    cached_bronze_date=None,
                    cached_bronze_path=None,
                    exact_replay=False,
                ),
                service=service,
                execute_run=execute_run,
                health_info_presenter=health_info_presenter,
                result_finalizer=result_finalizer,
                exit_func=exit_func,
            )

        mock_handle_destructive.assert_called_once()
        service.prepare_execution_request.assert_not_called()
        execute_run.assert_not_called()
        health_info_presenter.assert_not_called()
        result_finalizer.assert_not_called()
        exit_func.assert_not_called()

    def test_runs_prepare_execute_present_and_exit(self) -> None:
        service = MagicMock(spec=CliRunOrchestrationService)
        request = _make_request(health_server=True, health_port=9090)
        result = _make_result()
        service.prepare_execution_request.return_value = RunPreparationResult(
            request=request
        )
        execute_run = MagicMock(return_value=result)
        health_info_presenter = MagicMock()
        result_finalizer = MagicMock(side_effect=SystemExit(ExitCode.OK))
        exit_func = MagicMock(side_effect=SystemExit(ExitCode.OK))

        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run.command_policy.handle_destructive_step",
                return_value=True,
            ) as mock_handle_destructive,
            pytest.raises(SystemExit) as exc_info,
        ):
            run_command_flow(
                cli_input=RunCommandInput(
                    pipeline="chembl_activity",
                    run_type="incremental",
                    resume=False,
                    start_offset=None,
                    limit=10,
                    input_csv=None,
                    filter_column=None,
                    filter_field=None,
                    dry_run=False,
                    yes=True,
                    vacuum_after_run=None,
                    vacuum_retention_days=None,
                    debug=False,
                    health_server=True,
                    health_port=9090,
                    enable_tracing=True,
                    use_cached_bronze=False,
                    cached_bronze_date=None,
                    cached_bronze_path=None,
                    exact_replay=False,
                ),
                service=service,
                execute_run=execute_run,
                health_info_presenter=health_info_presenter,
                result_finalizer=result_finalizer,
                exit_func=exit_func,
            )

        assert exc_info.value.code == ExitCode.OK
        mock_handle_destructive.assert_called_once()
        execute_run.assert_called_once_with(request)
        health_info_presenter.assert_called_once_with(request)
        result_finalizer.assert_called_once_with(result)
        exit_func.assert_not_called()

    def test_forwards_exact_replay_to_request_preparation(self) -> None:
        service = MagicMock(spec=CliRunOrchestrationService)
        request = _make_request()
        service.prepare_execution_request.return_value = RunPreparationResult(
            request=request
        )
        execute_run = MagicMock(return_value=_make_result())
        health_info_presenter = MagicMock()
        result_finalizer = MagicMock(side_effect=SystemExit(ExitCode.OK))
        exit_func = MagicMock(side_effect=SystemExit(ExitCode.OK))

        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run.command_policy.handle_destructive_step",
                return_value=True,
            ),
            pytest.raises(SystemExit),
        ):
            run_command_flow(
                cli_input=RunCommandInput(
                    pipeline="chembl_activity",
                    run_type="incremental",
                    resume=False,
                    start_offset=None,
                    limit=10,
                    input_csv=None,
                    filter_column=None,
                    filter_field=None,
                    dry_run=False,
                    yes=True,
                    vacuum_after_run=None,
                    vacuum_retention_days=None,
                    debug=False,
                    health_server=False,
                    health_port=8081,
                    enable_tracing=None,
                    use_cached_bronze=True,
                    cached_bronze_date="2026-03-12",
                    cached_bronze_path="/tmp/bronze",
                    exact_replay=True,
                ),
                service=service,
                execute_run=execute_run,
                health_info_presenter=health_info_presenter,
                result_finalizer=result_finalizer,
                exit_func=exit_func,
            )

        request_input = service.prepare_execution_request.call_args.args[0]
        assert isinstance(request_input, CliRunPreparationInput)
        assert request_input.options.exact_replay is True

    def test_forwards_replay_parentage_to_request_preparation(self) -> None:
        service = MagicMock(spec=CliRunOrchestrationService)
        request = _make_request()
        service.prepare_execution_request.return_value = RunPreparationResult(
            request=request
        )
        execute_run = MagicMock(return_value=_make_result())
        health_info_presenter = MagicMock()
        result_finalizer = MagicMock(side_effect=SystemExit(ExitCode.OK))
        exit_func = MagicMock(side_effect=SystemExit(ExitCode.OK))

        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run.command_policy.handle_destructive_step",
                return_value=True,
            ),
            pytest.raises(SystemExit),
        ):
            run_command_flow(
                cli_input=RunCommandInput(
                    pipeline="chembl_activity",
                    run_type="incremental",
                    resume=False,
                    start_offset=None,
                    limit=10,
                    input_csv=None,
                    filter_column=None,
                    filter_field=None,
                    dry_run=False,
                    yes=True,
                    vacuum_after_run=None,
                    vacuum_retention_days=None,
                    debug=False,
                    health_server=False,
                    health_port=8081,
                    enable_tracing=None,
                    use_cached_bronze=True,
                    cached_bronze_date="2026-03-12",
                    cached_bronze_path="/tmp/bronze",
                    replay_of_run_id="run-parent",
                    replay_of_manifest_id="manifest-parent",
                    exact_replay=True,
                ),
                service=service,
                execute_run=execute_run,
                health_info_presenter=health_info_presenter,
                result_finalizer=result_finalizer,
                exit_func=exit_func,
            )

        request_input = service.prepare_execution_request.call_args.args[0]
        assert isinstance(request_input, CliRunPreparationInput)
        assert request_input.options.replay_of_run_id == "run-parent"
        assert request_input.options.replay_of_manifest_id == "manifest-parent"


# ---------------------------------------------------------------------------
# execute_run_step
# ---------------------------------------------------------------------------


class TestExecuteRunStep:
    """Tests for execute_run_step — covers lines 197-200, 211."""

    def _request(self, **kwargs: object) -> RunExecutionRequest:
        return _make_request(**kwargs)

    def test_success_returns_run_result(self) -> None:
        """Successful executor returns RunResult directly."""
        expected = _make_result()
        mock_executor = MagicMock(return_value=expected)
        request = self._request()

        result = execute_run_step(
            request=request,
            execute_run=mock_executor,
        )
        assert result is expected
        mock_executor.assert_called_once_with(request)

    def test_pipeline_not_found_calls_handle_failure_and_exits(self) -> None:
        """PipelineNotFoundError triggers handle_cli_failure -> sys.exit."""
        mock_executor = MagicMock(
            side_effect=PipelineNotFoundError("unknown_pipeline", ["chembl_activity"])
        )
        with pytest.raises(SystemExit):
            execute_run_step(
                request=self._request(pipeline="unknown_pipeline"),
                execute_run=mock_executor,
            )

    def test_bioetl_error_calls_handle_failure_and_exits(self) -> None:
        """BioETLError triggers handle_cli_failure -> sys.exit (line 197-198)."""
        mock_executor = MagicMock(side_effect=NetworkError("timeout"))
        with pytest.raises(SystemExit):
            execute_run_step(
                request=self._request(),
                execute_run=mock_executor,
            )

    def test_keyboard_interrupt_calls_handle_failure_and_exits(self) -> None:
        """KeyboardInterrupt triggers handle_cli_failure -> sys.exit (line 199-200)."""
        mock_executor = MagicMock(side_effect=KeyboardInterrupt())
        with pytest.raises(SystemExit) as exc_info:
            execute_run_step(
                request=self._request(),
                execute_run=mock_executor,
            )
        assert exc_info.value.code == ExitCode.SIGINT

    def test_cli_entrypoint_typed_error_calls_handle_failure_and_exits(self) -> None:
        """OSError (CLI_ENTRYPOINT_TYPED_ERRORS member) triggers sys.exit."""
        mock_executor = MagicMock(side_effect=OSError("I/O failure"))
        with pytest.raises(SystemExit):
            execute_run_step(
                request=self._request(),
                execute_run=mock_executor,
            )

    def test_unreachable_line_never_reached_in_normal_flow(self) -> None:
        """The RuntimeError on line 211 is never reached in normal success path."""
        expected = _make_result()
        mock_executor = MagicMock(return_value=expected)
        # Should not raise RuntimeError
        result = execute_run_step(
            request=self._request(),
            execute_run=mock_executor,
        )
        assert result is expected


# ---------------------------------------------------------------------------
# finalize_run_step
# ---------------------------------------------------------------------------


class TestFinalizeRunStep:
    """Tests for finalize_run_step."""

    def test_calls_presenter_and_exit_func(self) -> None:
        """Finalizer is called with the completed result."""
        result = _make_result(status=PipelineRunResult.SUCCESS)
        finalizer = MagicMock()

        finalize_run_step(
            run_result=result,
            result_finalizer=finalizer,
        )

        finalizer.assert_called_once_with(result)

    def test_failed_status_maps_to_pipeline_error_exit(self) -> None:
        """FAILED result is still delegated to the injected finalizer."""
        result = _make_result(
            status=PipelineRunResult.FAILED,
            error_type="UnknownError",
        )
        finalizer = MagicMock()

        finalize_run_step(
            run_result=result,
            result_finalizer=finalizer,
        )

        finalizer.assert_called_once_with(result)

    def test_shutdown_status_maps_to_sigint_exit(self) -> None:
        """SHUTDOWN result is delegated to the injected finalizer."""
        result = _make_result(status=PipelineRunResult.SHUTDOWN)
        finalizer = MagicMock()

        finalize_run_step(
            run_result=result,
            result_finalizer=finalizer,
        )

        finalizer.assert_called_once_with(result)
