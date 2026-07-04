"""Private result/presentation helpers for CLI run command finalization."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from bioetl.application.services.execution.cli_run_orchestration_models import (
    RunExecutionRequest,
)
from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    echo_health_server_info,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.execution.pipeline_runner_models import (
        PipelineRunResult,
    )
    from bioetl.interfaces.cli.exit_codes import ExitCode


def present_run_health_info(
    request: RunExecutionRequest,
    *,
    info_presenter: Callable[[bool, int], None] = echo_health_server_info,
) -> None:
    """Render health-server info for a prepared run request."""
    info_presenter(request.health_server, request.health_port)


def finalize_run_result(
    result: RunResult,
    *,
    presenter: Callable[[RunResult], None],
    status_mapper: Callable[[PipelineRunResult, str | None], ExitCode],
    exit_func: Callable[[int | str | None], NoReturn],
) -> NoReturn:
    """Present run result and exit using mapped status code."""
    presenter(result)
    exit_func(status_mapper(result.status, result.error_type))
