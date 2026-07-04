"""Dependency bundles for the public run-all runtime seam."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn

import click

from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
    RunAllCommandInput,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import BatchRunResult

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.interfaces.cli.exit_codes import ExitCode


@dataclass(frozen=True, slots=True)
class RunAllCallbackRuntime:
    """Dependencies used by the public run-all Click callback."""

    build_probe_paths: Callable[[], tuple[str, ...]]
    build_cli_input_from_options: Callable[[Mapping[str, object]], RunAllCommandInput]
    build_input: Callable[..., RunAllCommandInput]
    dispatch_cli_callback: Callable[..., None]
    disable_transient_health_server: Callable[..., bool]
    ensure_observability_backend_started: Callable[..., object]
    run_with_cli_policy: Callable[[click.Context, RunAllCommandInput], None]


@dataclass(frozen=True, slots=True)
class RunAllPolicyRuntime:
    """Dependencies used after normalized CLI input is available."""

    build_cli_registry: Callable[[], PipelineRegistry]
    destructive_confirmation: Callable[[str, list[str], bool, bool], bool]
    determine_exit_code: Callable[[BatchRunResult], ExitCode]
    execute_batch: Callable[..., BatchRunResult | None]
    exit_func: Callable[[int | str | None], NoReturn]
    health_info_presenter: Callable[[bool, int], None]
    listing_emitter: Callable[..., None]
    preview_emitter: Callable[..., None]
    resolve_context_registry: Callable[[click.Context], PipelineRegistry | None]
    run_all_command_flow: Callable[..., None]
    summary_presenter: Callable[[BatchRunResult, bool], None]


@dataclass(frozen=True, slots=True)
class RunAllBatchRuntime:
    """Dependencies used by sync/async run-all batch execution."""

    ensure_metrics_server_started: Callable[[], object]
    get_pipeline_runner_service: Callable[..., PipelineRunnerService]
    handle_failure: Callable[..., None]
    health_server_context_factory: Callable[..., object]
    run_coro: Callable[[Awaitable[BatchRunResult]], BatchRunResult]


@dataclass(frozen=True, slots=True)
class RunAllPresentationRuntime:
    """Output and confirmation dependencies for public run-all helpers."""

    confirm: Callable[[str], bool]
    error_printer: Callable[..., None]
    exit_func: Callable[[int | str | None], NoReturn]
    info_printer: Callable[..., None]


__all__ = [
    "RunAllBatchRuntime",
    "RunAllCallbackRuntime",
    "RunAllPolicyRuntime",
    "RunAllPresentationRuntime",
]
