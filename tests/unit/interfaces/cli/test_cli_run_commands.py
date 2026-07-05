"""Unit tests for CLI run and run-all command seams."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestMapStatusToExitCode:
    """Tests for _map_status_to_exit_code function."""

    def test_success_status(self):
        """Test SUCCESS status maps to OK."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.SUCCESS, None)

        assert result == ExitCode.OK

    def test_dry_run_status(self):
        """Test DRY_RUN status maps to OK."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.DRY_RUN, None)

        assert result == ExitCode.OK

    def test_shutdown_status(self):
        """Test SHUTDOWN status maps to SIGINT."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.SHUTDOWN, None)

        assert result == ExitCode.SIGINT

    def test_failed_with_value_error(self):
        """Test FAILED with ValueError maps to CONFIG_ERROR."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, "ValueError")

        assert result == ExitCode.CONFIG_ERROR

    def test_failed_with_data_quality_error(self):
        """Test FAILED with DataQualityError maps to DATA_QUALITY_ERROR."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, "DataQualityError")

        assert result == ExitCode.DATA_QUALITY_ERROR

    def test_failed_with_lock_error(self):
        """Test FAILED with LockAcquisitionError maps to LOCK_ERROR."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(
            PipelineRunResult.FAILED, "LockAcquisitionError"
        )

        assert result == ExitCode.LOCK_ERROR

    def test_failed_with_network_error(self):
        """Test FAILED with NetworkError maps to NETWORK_ERROR."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, "NetworkError")

        assert result == ExitCode.NETWORK_ERROR

    def test_failed_with_unknown_error(self):
        """Test FAILED with unknown error type maps to PIPELINE_ERROR."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, "SomeUnknownError")

        assert result == ExitCode.PIPELINE_ERROR

    def test_failed_without_error_type(self):
        """Test FAILED without error type maps to PIPELINE_ERROR."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, None)

        assert result == ExitCode.PIPELINE_ERROR


@pytest.mark.unit
def test_run_prepared_request_async_uses_compat_runtime_path():
    """Prepared CLI request should still delegate through _run_pipeline_async."""
    import asyncio

    from bioetl.application.services.execution.cli_run_orchestration_models import (
        RunExecutionRequest,
    )
    from bioetl.application.services.execution.pipeline_runner_models import (
        PipelineRunResult,
        RunResult,
    )
    from bioetl.interfaces.cli.commands import run as run_module

    options = MagicMock(name="run_options")
    request = RunExecutionRequest(
        pipeline="chembl_activity",
        options=options,
        health_server=False,
        health_port=8081,
    )
    expected = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name="chembl_activity",
        run_id="test-run-id",
        run_type="incremental",
    )
    registry = MagicMock(name="registry")

    with patch(
        "bioetl.interfaces.cli.commands.run._run_pipeline_async",
        new=AsyncMock(return_value=expected),
    ) as mock_run_pipeline_async:
        result = asyncio.run(
            run_module._run_prepared_request_async(request, registry=registry)
        )

    assert result is expected
    mock_run_pipeline_async.assert_awaited_once_with(
        "chembl_activity",
        options,
        health_server_enabled=False,
        health_port=8081,
        registry=registry,
    )


@pytest.mark.unit
def test_run_module_declares_expected_seam_inventory() -> None:
    """run.py should keep an explicit inventory of canonical command seams."""
    from bioetl.interfaces.cli.commands import run as run_module

    assert run_module._RUN_CANONICAL_BOUNDARY_SEAMS == (
        "create_cli_run_orchestration_service",
        "get_cli_run_orchestration_service",
        "_build_run_command_input",
        "_build_run_pipeline_callable",
        "_map_status_to_exit_code",
        "_present_run_health_info",
        "_finalize_run_result",
        "_run_pipeline_async",
        "_run_prepared_request_async",
    )
    assert not hasattr(run_module, "_RUN_COMPATIBILITY_SEAMS")

    for seam_name in run_module._RUN_CANONICAL_BOUNDARY_SEAMS:
        assert hasattr(run_module, seam_name)

    assert (
        run_module._build_run_command_input is run_module._build_run_command_input_impl
    )
    assert (
        run_module._build_run_pipeline_callable
        is run_module._build_run_pipeline_callable_impl
    )
    assert run_module._map_status_to_exit_code is run_module.map_status_to_exit_code
    assert (
        run_module.echo_health_server_info is run_module._echo_health_server_info_impl
    )
    assert (
        run_module.ensure_metrics_server_started
        is run_module._ensure_metrics_server_started_impl
    )
    assert run_module.health_server_context is run_module._health_server_context_impl
    assert not hasattr(run_module, "get_pipeline_runner_service")


@pytest.mark.unit
def test_execute_run_uses_canonical_runtime_callable_builder() -> None:
    """execute_run should delegate prepared-request runtime wiring to helper builder."""
    from bioetl.interfaces.cli.commands import run as run_module

    request = MagicMock(name="prepared_request")
    registry = MagicMock(name="registry")
    expected = MagicMock(name="run_result")
    run_pipeline_callable = AsyncMock(name="run_pipeline_callable")
    service = MagicMock(name="cli_run_service")
    service.execute_pipeline.return_value = expected

    with (
        patch.object(
            run_module,
            "_build_run_pipeline_callable",
            return_value=run_pipeline_callable,
        ) as mock_build_callable,
        patch.object(
            run_module,
            "create_cli_run_orchestration_service",
            return_value=service,
        ),
    ):
        result = run_module.execute_run(request, registry=registry)

    assert result is expected
    mock_build_callable.assert_called_once_with(
        registry=registry,
        run_pipeline_async_callable=run_module._run_pipeline_async,
    )
    service.execute_pipeline.assert_called_once_with(
        request=request,
        run_pipeline_async=run_pipeline_callable,
        run_coroutine=run_module.asyncio.run,
        flush_metrics=ANY,
    )


@pytest.mark.unit
def test_finalize_run_result_presents_and_exits() -> None:
    """CLI finalizer should render output before terminating with mapped exit code."""
    from bioetl.application.services.execution.pipeline_runner_models import (
        PipelineRunResult,
        RunResult,
    )
    from bioetl.interfaces.cli.commands import run as run_module
    from bioetl.interfaces.cli.exit_codes import ExitCode

    result = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name="chembl_activity",
        run_id="test-run-id",
        run_type="incremental",
    )

    with (
        patch.object(run_module, "_echo_run_result") as mock_presenter,
        patch.object(run_module, "_exit_with_code") as mock_exit,
        patch.object(
            run_module,
            "_map_status_to_exit_code",
            return_value=ExitCode.OK,
        ) as mock_map_status,
    ):
        run_module._finalize_run_result(result)

    mock_presenter.assert_called_once_with(result)
    mock_map_status.assert_called_once_with(PipelineRunResult.SUCCESS, None)
    mock_exit.assert_called_once_with(ExitCode.OK)


@pytest.mark.unit
def test_run_command_with_cli_policy_wires_registry_and_cli_seams() -> None:
    """CLI policy helper should resolve registry and inject canonical run seams."""
    from bioetl.interfaces.cli.commands import run as run_module
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        RunCommandInput,
    )

    ctx = MagicMock(name="click_context")
    registry = MagicMock(name="registry")
    cli_input = RunCommandInput(
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
        enable_tracing=True,
        use_cached_bronze=False,
        cached_bronze_date=None,
        cached_bronze_path=None,
    )

    with (
        patch.object(
            run_module,
            "resolve_context_registry",
            return_value=registry,
        ) as mock_resolve_registry,
        patch.object(
            run_module,
            "ensure_observability_backend_started",
        ) as mock_ensure_backend,
        patch.object(
            run_module,
            "should_disable_transient_health_server",
            return_value=False,
        ) as mock_disable_transient,
        patch.object(run_module, "run_command_flow") as mock_run_command_flow,
    ):
        run_module._run_command_with_cli_policy(ctx, cli_input)

    mock_resolve_registry.assert_called_once_with(ctx)
    mock_ensure_backend.assert_called_once_with(
        enabled=True,
        port=8081,
        required_probe_paths=("/ops/control-plane/ready",),
    )
    mock_disable_transient.assert_called_once()
    assert mock_run_command_flow.call_count == 1
    kwargs = mock_run_command_flow.call_args.kwargs
    assert kwargs["cli_input"] is cli_input
    compatibility_service = run_module.get_cli_run_orchestration_service()
    assert kwargs["service"] is not compatibility_service
    assert type(kwargs["service"]) is type(compatibility_service)
    assert kwargs["health_info_presenter"] is run_module._present_run_health_info
    assert kwargs["result_finalizer"] is run_module._finalize_run_result
    assert kwargs["exit_func"] is run_module._exit_with_code
    execute_run_callable = kwargs["execute_run"]
    assert execute_run_callable.func is run_module.execute_run
    assert execute_run_callable.keywords == {"registry": registry}


@pytest.mark.unit
def test_run_command_with_cli_policy_disables_transient_health_server_on_live_backend() -> (
    None
):
    """CLI helper should pass a downgraded input when detached backend replaces the HTTP server."""
    from bioetl.interfaces.cli.commands import run as run_module
    from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
        ObservabilityBackendEnsureResult,
    )
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        RunCommandInput,
    )

    ctx = MagicMock(name="click_context")
    registry = MagicMock(name="registry")
    cli_input = RunCommandInput(
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
        enable_tracing=True,
        use_cached_bronze=False,
        cached_bronze_date=None,
        cached_bronze_path=None,
    )
    backend_result = ObservabilityBackendEnsureResult(
        status="reused",
        health_url="http://127.0.0.1:8081/health",
    )

    with (
        patch.object(
            run_module,
            "resolve_context_registry",
            return_value=registry,
        ),
        patch.object(
            run_module,
            "ensure_observability_backend_started",
            return_value=backend_result,
        ) as mock_ensure_backend,
        patch.object(
            run_module,
            "should_disable_transient_health_server",
            return_value=True,
        ) as mock_disable_transient,
        patch.object(run_module, "run_command_flow") as mock_run_command_flow,
    ):
        run_module._run_command_with_cli_policy(ctx, cli_input)

    mock_ensure_backend.assert_called_once_with(
        enabled=True,
        port=8081,
        required_probe_paths=("/ops/control-plane/ready",),
    )
    mock_disable_transient.assert_called_once_with(
        health_server_enabled=True,
        health_port=8081,
        observability_backend_port=8081,
        backend_result=backend_result,
    )
    kwargs = mock_run_command_flow.call_args.kwargs
    assert kwargs["cli_input"] is not cli_input
    assert kwargs["cli_input"].health_server is False
    assert kwargs["cli_input"].health_port == cli_input.health_port


@pytest.mark.unit
def test_run_callback_delegates_to_input_builder_and_cli_policy() -> None:
    """Click callback should stay a thin entrypoint over the run-policy seams."""
    from bioetl.interfaces.cli.commands import run as run_module
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        RunCommandInput,
    )

    ctx = MagicMock(name="click_context")
    cli_input = MagicMock(name="cli_input")

    with (
        patch.object(
            run_module,
            "_build_run_command_input",
            return_value=cli_input,
        ) as mock_build_input,
        patch.object(
            run_module,
            "_run_command_with_cli_policy",
        ) as mock_run_with_policy,
    ):
        run_module.run.callback.__wrapped__(
            ctx,
            pipeline="chembl_activity",
            run_type="incremental",
            resume=False,
            start_offset=None,
            limit=10,
            input_csv=None,
            filter_column="compound_id",
            filter_field="compound_id",
            dry_run=False,
            yes=True,
            vacuum_after_run=None,
            vacuum_retention_days=None,
            debug=False,
            health_server=True,
            health_port=8081,
            enable_tracing=True,
            use_cached_bronze=False,
            cached_bronze_date=None,
            cached_bronze_path=None,
            replay_of_run_id=None,
            replay_of_manifest_id=None,
            resume_run_id=None,
            resume_manifest_id=None,
            exact_replay=False,
            required_persistence_profile="degraded_observable",
        )

    mock_build_input.assert_called_once()
    assert mock_build_input.call_args.args == (
        RunCommandInput(
            pipeline="chembl_activity",
            run_type="incremental",
            resume=False,
            start_offset=None,
            limit=10,
            input_csv=None,
            filter_column="compound_id",
            filter_field="compound_id",
            dry_run=False,
            yes=True,
            vacuum_after_run=None,
            vacuum_retention_days=None,
            debug=False,
            health_server=True,
            health_port=8081,
            enable_tracing=True,
            use_cached_bronze=False,
            cached_bronze_date=None,
            cached_bronze_path=None,
            replay_of_run_id=None,
            replay_of_manifest_id=None,
            resume_run_id=None,
            resume_manifest_id=None,
            exact_replay=False,
            required_persistence_profile="degraded_observable",
        ),
    )
    assert mock_build_input.call_args.kwargs == {}
    mock_run_with_policy.assert_called_once_with(ctx, cli_input)


@pytest.mark.unit
def test_run_all_with_cli_policy_wires_registry_and_cli_seams() -> None:
    """Run-all policy helper should resolve registry and inject canonical seams."""
    from bioetl.interfaces.cli.commands import run_all as run_all_module
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        RunAllCommandInput,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        determine_batch_exit_code,
    )

    ctx = MagicMock(name="click_context")
    registry = MagicMock(name="registry")
    cli_input = RunAllCommandInput(
        source="chembl",
        run_type="incremental",
        limit=None,
        dry_run=False,
        yes=True,
        list_only=False,
        debug=False,
        health_server=True,
        health_port=8081,
    )

    with (
        patch.object(
            run_all_module,
            "resolve_context_registry",
            return_value=registry,
        ) as mock_resolve_registry,
        patch(
            "bioetl.interfaces.cli.commands.run_all.run_all_command_flow"
        ) as mock_run_all_command_flow,
    ):
        run_all_module._run_all_with_cli_policy(ctx, cli_input)

    mock_resolve_registry.assert_called_once_with(ctx)
    assert mock_run_all_command_flow.call_count == 1
    kwargs = mock_run_all_command_flow.call_args.kwargs
    assert kwargs["cli_input"] is cli_input
    assert kwargs["registry"] is registry
    assert (
        kwargs["destructive_confirmation"]
        is run_all_module._handle_destructive_confirmation
    )
    assert kwargs["listing_emitter"] is run_all_module.emit_run_all_listing
    assert kwargs["preview_emitter"] is run_all_module.emit_run_all_preview
    assert kwargs["health_info_presenter"] is run_all_module.echo_health_server_info
    assert kwargs["execute_batch"] is run_all_module._run_batch_with_policy
    assert kwargs["summary_presenter"] is run_all_module._echo_batch_summary
    assert kwargs["determine_exit_code"] is determine_batch_exit_code
    assert kwargs["exit_func"] is run_all_module.exit_with_code


@pytest.mark.unit
def test_run_all_callback_ensures_observability_backend_with_catalog_probe() -> None:
    from bioetl.interfaces.cli.commands import run_all as run_all_module
    from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
        ObservabilityBackendEnsureResult,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        RunAllCommandInput,
    )

    ctx = MagicMock(name="click_context")
    cli_input = RunAllCommandInput(
        source="chembl",
        run_type="incremental",
        limit=None,
        dry_run=False,
        yes=True,
        list_only=False,
        debug=False,
        health_server=True,
        health_port=8081,
    )
    backend_result = ObservabilityBackendEnsureResult(
        status="reused",
        health_url="http://127.0.0.1:8081/health",
    )

    with (
        patch.object(
            run_all_module,
            "_build_run_all_command_input_from_options",
            return_value=cli_input,
        ),
        patch.object(
            run_all_module,
            "ensure_observability_backend_started",
            return_value=backend_result,
        ) as mock_ensure_backend,
        patch.object(
            run_all_module,
            "should_disable_transient_health_server",
            return_value=False,
        ) as mock_disable_transient,
        patch(
            "bioetl.interfaces.cli.commands.run_all.dispatch_cli_callback"
        ) as mock_dispatch,
    ):
        run_all_module._run_all_callback(
            ctx,
            source="chembl",
            run_type="incremental",
            limit=None,
            dry_run=False,
            yes=True,
            list_only=False,
            debug=False,
            health_server=True,
            health_port=8081,
            ensure_observability_backend=True,
            observability_backend_port=8081,
        )

    mock_ensure_backend.assert_called_once_with(
        enabled=True,
        port=8081,
        required_probe_paths=("/ops/control-plane/ready",),
    )
    mock_disable_transient.assert_called_once_with(
        health_server_enabled=True,
        health_port=8081,
        observability_backend_port=8081,
        backend_result=backend_result,
    )
    mock_dispatch.assert_called_once()


@dataclass
class MockRunResult:
    """Mock RunResult for testing."""

    status: object
    error_message: str | None = None
    error_type: str | None = None


@pytest.mark.unit
class TestRunCommandExceptionHandlers:
    """Tests for exception handlers in run command."""

    def test_run_pipeline_not_found(self, capsys):
        """Test run execution step handles PipelineNotFoundError."""
        from bioetl.application.services.execution.cli_run_orchestration_models import (
            RunExecutionRequest,
        )
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineNotFoundError,
            RunOptions,
        )
        from bioetl.interfaces.cli.commands.domains.run.command_policy import (
            execute_run_step,
        )

        with pytest.raises(SystemExit) as exc_info:
            execute_run_step(
                request=RunExecutionRequest(
                    pipeline="foo",
                    options=RunOptions(),
                    health_server=True,
                    health_port=8080,
                ),
                execute_run=MagicMock(
                    side_effect=PipelineNotFoundError("foo", available=["bar", "baz"])
                ),
            )

        captured = capsys.readouterr()
        assert exc_info.value.code == 80
        assert "Pipeline not found" in captured.err

    def test_run_unexpected_exception(self, capsys):
        """Test run execution step handles unexpected exceptions."""
        from bioetl.application.services.execution.cli_run_orchestration_models import (
            RunExecutionRequest,
        )
        from bioetl.application.services.execution.pipeline_runner_models import (
            RunOptions,
        )
        from bioetl.interfaces.cli.commands.domains.run.command_policy import (
            execute_run_step,
        )

        with pytest.raises(SystemExit) as exc_info:
            execute_run_step(
                request=RunExecutionRequest(
                    pipeline="foo",
                    options=RunOptions(),
                    health_server=True,
                    health_port=8080,
                ),
                execute_run=MagicMock(side_effect=RuntimeError("Unexpected failure")),
            )

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert "Unexpected error" in captured.err


@pytest.mark.unit
class TestShowCleanupPreview:
    """Tests for show_cleanup_preview function."""

    def test_show_cleanup_preview_success(self, capsys):
        """Test show_cleanup_preview success path."""
        from bioetl.interfaces.cli.commands.domains.run.support import (
            show_cleanup_preview,
        )

        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support._preview_cleanup_async",
            new_callable=AsyncMock,
        ) as mock_preview:
            show_cleanup_preview("chembl_activity")

        mock_preview.assert_awaited_once_with("chembl_activity")

    def test_show_cleanup_preview_error(self, capsys):
        """Test show_cleanup_preview handles errors."""
        from bioetl.interfaces.cli.commands.domains.run.support import (
            show_cleanup_preview,
        )

        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support._preview_cleanup_async",
            side_effect=RuntimeError("Preview failed"),
        ):
            show_cleanup_preview("chembl_activity")

        captured = capsys.readouterr()
        assert "Error previewing cleanup" in captured.err
