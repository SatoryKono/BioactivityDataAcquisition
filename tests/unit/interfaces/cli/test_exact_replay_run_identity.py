"""The CLI must carry an explicit replay execution ID to the guarded runner."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from functools import partial
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from click.testing import CliRunner

from bioetl.application.services.execution.cli_run_orchestration_models import (
    RunExecutionRequest,
    RunPreparationResult,
)
from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.interfaces.cli.commands import run as run_module
from bioetl.interfaces.cli.commands.domains.run.command_entrypoint import (
    build_run_click_command,
)
from bioetl.interfaces.cli.commands.domains.run.command_policy import (
    prepare_run_request,
)
from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
    run_pipeline_async,
    run_prepared_request_async,
)

EXECUTION_ID = UUID("baf23039-0fc0-4985-a2eb-b4cd226aaf57")
PARENT_ID = "75289a8a-402b-54ae-a27b-33a51ecac194"
pytestmark = pytest.mark.unit


def _command(callback):
    return build_run_click_command(
        validate_pipeline_name=lambda _ctx, _param, value: value,
        default_health_server_port=8000,
        run_callback=callback,
    )


def test_click_run_id_reaches_prepared_execution_without_changing_parentage():
    received = []

    def callback(_ctx, **options):
        received.append(run_module._build_run_command_input_from_options(options))

    result = CliRunner().invoke(
        _command(callback),
        [
            "--pipeline",
            "chembl_activity",
            "--exact-replay",
            "--use-cached-bronze",
            "--run-id",
            str(EXECUTION_ID),
            "--replay-of-run-id",
            PARENT_ID,
        ],
    )
    assert result.exit_code == 0, result.output
    options = RunOptions(exact_replay=True, use_cached_bronze=True)
    original = RunExecutionRequest("chembl_activity", options, False, 8000)
    service = MagicMock()
    service.prepare_execution_request.return_value = RunPreparationResult(
        request=original
    )
    prepared = prepare_run_request(
        service=service, command_input=received[0], exit_func=MagicMock()
    )
    assert prepared.run_id == EXECUTION_ID
    assert original.run_id is None
    assert received[0].replay_of_run_id == PARENT_ID
    assert (
        service.prepare_execution_request.call_args.args[0].options.replay_of_run_id
        == PARENT_ID
    )


def test_invalid_execution_uuid_is_rejected_before_callback():
    callback = MagicMock()
    result = CliRunner().invoke(
        _command(callback), ["--pipeline", "chembl_activity", "--run-id", "invalid"]
    )
    assert result.exit_code == 2
    callback.assert_not_called()


def test_prepared_request_passes_execution_id_to_runner_service():
    options = RunOptions(exact_replay=True, use_cached_bronze=True)
    request = RunExecutionRequest("chembl_activity", options, False, 8000, EXECUTION_ID)
    service = MagicMock()
    expected = object()
    service.run = AsyncMock(return_value=expected)

    @asynccontextmanager
    async def health_context(**_kwargs):
        yield None

    execute = partial(
        run_pipeline_async,
        metrics_starter=lambda: True,
        health_context_factory=health_context,
        runner_service_factory=lambda **_kwargs: service,
    )
    result = asyncio.run(
        run_prepared_request_async(request, run_pipeline_async_callable=execute)
    )
    assert result is expected
    service.run.assert_awaited_once_with(
        "chembl_activity", options=options, run_id=EXECUTION_ID
    )


def test_legacy_request_does_not_add_an_execution_id_keyword():
    options = RunOptions()
    request = RunExecutionRequest("chembl_activity", options, False, 8000)
    execute = AsyncMock()
    asyncio.run(
        run_prepared_request_async(request, run_pipeline_async_callable=execute)
    )
    assert "run_id" not in execute.await_args.kwargs


def test_public_run_bridge_preserves_explicit_execution_id(monkeypatch):
    execute = AsyncMock()
    monkeypatch.setattr(run_module, "_run_pipeline_async_impl", execute)
    options = RunOptions(exact_replay=True, use_cached_bronze=True)
    asyncio.run(
        run_module._run_pipeline_async("chembl_activity", options, run_id=EXECUTION_ID)
    )
    assert execute.await_args.kwargs["run_id"] == EXECUTION_ID
