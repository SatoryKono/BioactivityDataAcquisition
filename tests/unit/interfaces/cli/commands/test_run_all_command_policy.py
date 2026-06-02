"""Unit tests for canonical run-all command policy helpers."""

from __future__ import annotations

from unittest.mock import ANY, MagicMock, patch

import pytest

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.domain.exceptions import NetworkError
from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
    RunAllCommandInput,
    build_run_all_command_input,
    handle_run_all_cli_failure,
    prepare_run_all_execution_plan,
    run_all_command_flow,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    RunAllExecutionPlan,
)
from bioetl.interfaces.cli.exit_codes import ExitCode


pytestmark = pytest.mark.unit


def _make_cli_input(**kwargs: object) -> RunAllCommandInput:
    defaults: dict[str, object] = {
        "source": "chembl",
        "run_type": "incremental",
        "limit": None,
        "dry_run": False,
        "yes": True,
        "list_only": False,
        "debug": False,
        "health_server": True,
        "health_port": 8081,
    }
    defaults.update(kwargs)
    return RunAllCommandInput(**defaults)


def _make_plan(**kwargs: object) -> RunAllExecutionPlan:
    defaults: dict[str, object] = {
        "pipelines": ["chembl_activity", "chembl_assay"],
        "options": RunOptions(
            run_type="incremental",
            limit=None,
            dry_run=False,
            log_level="INFO",
        ),
    }
    defaults.update(kwargs)
    return RunAllExecutionPlan(**defaults)


class TestBuildRunAllCommandInput:
    """Tests for build_run_all_command_input helper."""

    def test_builds_normalized_cli_payload(self) -> None:
        cli_input = build_run_all_command_input(
            source="chembl",
            run_type="rebuild",
            limit=50,
            dry_run=True,
            yes=False,
            list_only=True,
            debug=True,
            health_server=False,
            health_port=9090,
        )

        assert cli_input == RunAllCommandInput(
            source="chembl",
            run_type="rebuild",
            limit=50,
            dry_run=True,
            yes=False,
            list_only=True,
            debug=True,
            health_server=False,
            health_port=9090,
        )

    def test_run_all_module_maps_click_kwargs_into_policy_input(self) -> None:
        from bioetl.interfaces.cli.commands import run_all as run_all_module

        cli_input = run_all_module._build_run_all_command_input_from_options(
            {
                "source": "chembl",
                "run_type": "incremental",
                "limit": 10,
                "dry_run": False,
                "yes": True,
                "list_only": False,
                "debug": False,
                "health_server": True,
                "health_port": 8081,
            }
        )

        assert cli_input == RunAllCommandInput(
            source="chembl",
            run_type="incremental",
            limit=10,
            dry_run=False,
            yes=True,
            list_only=False,
            debug=False,
            health_server=True,
            health_port=8081,
        )

    def test_run_all_callback_delegates_to_input_builder_and_cli_policy(self) -> None:
        """Run-all Click callback should stay a thin entrypoint over policy seams."""
        from bioetl.interfaces.cli.commands import run_all as run_all_module

        ctx = MagicMock(name="click_context")
        cli_input = MagicMock(name="cli_input")

        with (
            patch.object(
                run_all_module,
                "build_run_all_command_input",
                return_value=cli_input,
            ) as mock_build_input,
            patch.object(
                run_all_module,
                "_run_all_with_cli_policy",
            ) as mock_run_with_policy,
        ):
            run_all_module.run_all.callback.__wrapped__(
                ctx,
                source="chembl",
                run_type="incremental",
                limit=10,
                dry_run=False,
                yes=True,
                list_only=False,
                debug=False,
                health_server=True,
                health_port=8081,
                ensure_observability_backend=True,
                observability_backend_port=8081,
            )

        mock_build_input.assert_called_once_with(
            source="chembl",
            run_type="incremental",
            limit=10,
            dry_run=False,
            yes=True,
            list_only=False,
            debug=False,
            health_server=True,
            health_port=8081,
            ensure_observability_backend=True,
            observability_backend_port=8081,
        )
        mock_run_with_policy.assert_called_once_with(ctx, cli_input)


class TestHandleRunAllCliFailure:
    """Tests for shared run-all failure handling helper."""

    def test_domain_error_delegates_to_execution_policy(self) -> None:
        with pytest.raises(SystemExit):
            handle_run_all_cli_failure(
                NetworkError("upstream unavailable"),
                source="chembl",
                reason_code="CLI_RUN_ALL_DOMAIN_ERROR",
            )

    def test_keyboard_interrupt_exits_with_sigint(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            handle_run_all_cli_failure(
                KeyboardInterrupt(),
                source="chembl",
                reason_code="CLI_RUN_ALL_SIGINT",
            )

        assert exc_info.value.code == ExitCode.SIGINT


class TestPrepareRunAllExecutionPlan:
    """Tests for prepare_run_all_execution_plan helper."""

    def test_returns_execution_plan_when_provider_is_valid(self) -> None:
        expected_plan = _make_plan()

        with patch(
            "bioetl.interfaces.cli.commands.domains.run_all.command_policy.resolve_run_all_execution_plan",
            return_value=(expected_plan, None),
        ):
            result = prepare_run_all_execution_plan(
                cli_input=_make_cli_input(),
                registry=MagicMock(),
                exit_func=MagicMock(),
            )

        assert result is expected_plan

    def test_invalid_provider_echoes_error_and_exits(self) -> None:
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.command_policy.resolve_run_all_execution_plan",
                return_value=(None, "bad provider"),
            ),
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.command_policy.echo_error"
            ) as mock_error,
            pytest.raises(SystemExit) as exc_info,
        ):
            prepare_run_all_execution_plan(
                cli_input=_make_cli_input(),
                registry=MagicMock(),
                exit_func=MagicMock(side_effect=SystemExit(ExitCode.FAIL)),
            )

        assert exc_info.value.code == ExitCode.FAIL
        mock_error.assert_called_once_with("Provider error", "bad provider")


class TestRunAllCommandFlow:
    """Tests for run_all_command_flow orchestration."""

    def test_list_only_emits_listing_and_exits_ok(self) -> None:
        plan = _make_plan()
        destructive_confirmation = MagicMock()
        listing_emitter = MagicMock()
        preview_emitter = MagicMock()
        health_info_presenter = MagicMock()
        execute_batch = MagicMock()
        summary_presenter = MagicMock()
        determine_exit_code = MagicMock(return_value=ExitCode.OK)

        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.command_policy.prepare_run_all_execution_plan",
                return_value=plan,
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            run_all_command_flow(
                cli_input=_make_cli_input(list_only=True),
                registry=MagicMock(),
                destructive_confirmation=destructive_confirmation,
                listing_emitter=listing_emitter,
                preview_emitter=preview_emitter,
                health_info_presenter=health_info_presenter,
                execute_batch=execute_batch,
                summary_presenter=summary_presenter,
                determine_exit_code=determine_exit_code,
                exit_func=MagicMock(side_effect=SystemExit(ExitCode.OK)),
            )

        assert exc_info.value.code == ExitCode.OK
        listing_emitter.assert_called_once_with(
            source="chembl",
            pipelines=plan.pipelines,
        )
        destructive_confirmation.assert_not_called()
        preview_emitter.assert_not_called()
        health_info_presenter.assert_not_called()
        execute_batch.assert_not_called()
        summary_presenter.assert_not_called()
        determine_exit_code.assert_not_called()

    def test_executes_batch_and_finalizes_exit_code(self) -> None:
        plan = _make_plan()
        batch_result = BatchRunResult(total=2, succeeded=2)
        destructive_confirmation = MagicMock(return_value=True)
        listing_emitter = MagicMock()
        preview_emitter = MagicMock()
        health_info_presenter = MagicMock()
        execute_batch = MagicMock(return_value=batch_result)
        summary_presenter = MagicMock()
        determine_exit_code = MagicMock(return_value=ExitCode.OK)

        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.command_policy.prepare_run_all_execution_plan",
                return_value=plan,
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            run_all_command_flow(
                cli_input=_make_cli_input(),
                registry=MagicMock(),
                destructive_confirmation=destructive_confirmation,
                listing_emitter=listing_emitter,
                preview_emitter=preview_emitter,
                health_info_presenter=health_info_presenter,
                execute_batch=execute_batch,
                summary_presenter=summary_presenter,
                determine_exit_code=determine_exit_code,
                exit_func=MagicMock(side_effect=SystemExit(ExitCode.OK)),
            )

        assert exc_info.value.code == ExitCode.OK
        destructive_confirmation.assert_called_once_with(
            "incremental",
            plan.pipelines,
            False,
            True,
        )
        preview_emitter.assert_called_once_with(
            source="chembl",
            pipelines=plan.pipelines,
            dry_run=False,
        )
        health_info_presenter.assert_called_once_with(True, 8081)
        execute_batch.assert_called_once_with(
            source="chembl",
            pipelines=plan.pipelines,
            options=plan.options,
            health_server=True,
            health_port=8081,
            registry=ANY,
        )
        summary_presenter.assert_called_once_with(batch_result, False)
        determine_exit_code.assert_called_once_with(batch_result)
        listing_emitter.assert_not_called()

    def test_returns_without_finalizing_when_batch_execution_is_handled(self) -> None:
        plan = _make_plan()
        destructive_confirmation = MagicMock(return_value=True)
        preview_emitter = MagicMock()
        health_info_presenter = MagicMock()
        execute_batch = MagicMock(return_value=None)
        summary_presenter = MagicMock()
        determine_exit_code = MagicMock(return_value=ExitCode.OK)
        exit_func = MagicMock()

        with patch(
            "bioetl.interfaces.cli.commands.domains.run_all.command_policy.prepare_run_all_execution_plan",
            return_value=plan,
        ):
            run_all_command_flow(
                cli_input=_make_cli_input(),
                registry=MagicMock(),
                destructive_confirmation=destructive_confirmation,
                listing_emitter=MagicMock(),
                preview_emitter=preview_emitter,
                health_info_presenter=health_info_presenter,
                execute_batch=execute_batch,
                summary_presenter=summary_presenter,
                determine_exit_code=determine_exit_code,
                exit_func=exit_func,
            )

        summary_presenter.assert_not_called()
        determine_exit_code.assert_not_called()
        exit_func.assert_not_called()
