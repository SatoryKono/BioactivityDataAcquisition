"""Unit tests for run_command_policy.py.

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
    RunOptions,
    RunResult,
)
from bioetl.domain.exceptions import NetworkError
from bioetl.interfaces.cli.commands.run_command_policy import (
    execute_run_step,
    finalize_run_step,
    handle_cli_failure,
    handle_destructive_step,
    map_status_to_exit_code,
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


def _make_options(**kwargs: object) -> RunOptions:
    return RunOptions(**kwargs)  # type: ignore[arg-type]


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
                "bioetl.interfaces.cli.commands.run_command_policy.handle_destructive_run_confirmation",
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
            "bioetl.interfaces.cli.commands.run_command_policy.handle_destructive_run_confirmation",
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
            "bioetl.interfaces.cli.commands.run_command_policy.handle_destructive_run_confirmation",
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

    def test_generic_exception_returns_false(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Generic Exception is caught, handle_cli_failure called, returns False."""

        class _WeirdError(Exception):
            pass

        with patch(
            "bioetl.interfaces.cli.commands.run_command_policy.handle_destructive_run_confirmation",
            side_effect=_WeirdError("weird"),
        ):
            result = handle_destructive_step(
                pipeline="chembl_activity",
                run_type="rebuild",
                dry_run=True,
                yes=True,
            )
        assert result is False
        err = capsys.readouterr().err
        assert "Error previewing cleanup" in err


# ---------------------------------------------------------------------------
# execute_run_step
# ---------------------------------------------------------------------------


class TestExecuteRunStep:
    """Tests for execute_run_step — covers lines 197-200, 211."""

    def _options(self) -> RunOptions:
        return _make_options()

    def test_success_returns_run_result(self) -> None:
        """Successful executor returns RunResult directly."""
        expected = _make_result()
        mock_executor = MagicMock(return_value=expected)

        result = execute_run_step(
            pipeline="chembl_activity",
            options=self._options(),
            health_server=False,
            health_port=8081,
            execute_run=mock_executor,
        )
        assert result is expected

    def test_pipeline_not_found_calls_handle_failure_and_exits(self) -> None:
        """PipelineNotFoundError triggers handle_cli_failure -> sys.exit."""
        mock_executor = MagicMock(
            side_effect=PipelineNotFoundError("unknown_pipeline", ["chembl_activity"])
        )
        with pytest.raises(SystemExit):
            execute_run_step(
                pipeline="unknown_pipeline",
                options=self._options(),
                health_server=False,
                health_port=8081,
                execute_run=mock_executor,
            )

    def test_bioetl_error_calls_handle_failure_and_exits(self) -> None:
        """BioETLError triggers handle_cli_failure -> sys.exit (line 197-198)."""
        mock_executor = MagicMock(side_effect=NetworkError("timeout"))
        with pytest.raises(SystemExit):
            execute_run_step(
                pipeline="chembl_activity",
                options=self._options(),
                health_server=False,
                health_port=8081,
                execute_run=mock_executor,
            )

    def test_keyboard_interrupt_calls_handle_failure_and_exits(self) -> None:
        """KeyboardInterrupt triggers handle_cli_failure -> sys.exit (line 199-200)."""
        mock_executor = MagicMock(side_effect=KeyboardInterrupt())
        with pytest.raises(SystemExit) as exc_info:
            execute_run_step(
                pipeline="chembl_activity",
                options=self._options(),
                health_server=False,
                health_port=8081,
                execute_run=mock_executor,
            )
        assert exc_info.value.code == ExitCode.SIGINT

    def test_cli_entrypoint_typed_error_calls_handle_failure_and_exits(self) -> None:
        """OSError (CLI_ENTRYPOINT_TYPED_ERRORS member) triggers sys.exit."""
        mock_executor = MagicMock(side_effect=OSError("I/O failure"))
        with pytest.raises(SystemExit):
            execute_run_step(
                pipeline="chembl_activity",
                options=self._options(),
                health_server=False,
                health_port=8081,
                execute_run=mock_executor,
            )

    def test_unreachable_line_never_reached_in_normal_flow(self) -> None:
        """The RuntimeError on line 211 is never reached in normal success path."""
        expected = _make_result()
        mock_executor = MagicMock(return_value=expected)
        # Should not raise RuntimeError
        result = execute_run_step(
            pipeline="chembl_activity",
            options=self._options(),
            health_server=False,
            health_port=8081,
            execute_run=mock_executor,
        )
        assert result is expected


# ---------------------------------------------------------------------------
# finalize_run_step
# ---------------------------------------------------------------------------


class TestFinalizeRunStep:
    """Tests for finalize_run_step."""

    def test_calls_presenter_and_exit_func(self) -> None:
        """Presenter and exit_func are called with correct arguments."""
        result = _make_result(status=PipelineRunResult.SUCCESS)
        presenter = MagicMock()
        exit_func: MagicMock = MagicMock()

        finalize_run_step(
            result=result,
            result_presenter=presenter,
            exit_func=exit_func,
        )

        presenter.assert_called_once_with(result)
        exit_func.assert_called_once_with(ExitCode.OK)

    def test_failed_status_maps_to_pipeline_error_exit(self) -> None:
        """FAILED status maps to PIPELINE_ERROR exit code."""
        result = _make_result(
            status=PipelineRunResult.FAILED,
            error_type="UnknownError",
        )
        presenter = MagicMock()
        exit_func: MagicMock = MagicMock()

        finalize_run_step(
            result=result,
            result_presenter=presenter,
            exit_func=exit_func,
        )

        exit_func.assert_called_once_with(ExitCode.PIPELINE_ERROR)

    def test_shutdown_status_maps_to_sigint_exit(self) -> None:
        """SHUTDOWN status maps to SIGINT exit code."""
        result = _make_result(status=PipelineRunResult.SHUTDOWN)
        presenter = MagicMock()
        exit_func: MagicMock = MagicMock()

        finalize_run_step(
            result=result,
            result_presenter=presenter,
            exit_func=exit_func,
        )

        exit_func.assert_called_once_with(ExitCode.SIGINT)
