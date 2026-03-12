"""Run-all CLI command."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

from bioetl.application.services import (
    PipelineNotFoundError,
    RunOptions,
    RunResult,
)
from bioetl.composition.entrypoints import get_pipeline_runner_service
from bioetl.composition.registry import PipelineRegistry
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.run_all_helpers import (
    BatchRunResult,
    create_run_all_execution_plan,
    echo_batch_summary as _echo_batch_summary_impl,
    emit_run_all_listing,
    emit_run_all_preview,
    handle_destructive_confirmation as _handle_destructive_confirmation_impl,
    record_pipeline_failure,
    record_pipeline_result,
    should_prompt_for_destructive_run,
)
from bioetl.interfaces.cli.commands.run_all_helpers import (
    determine_batch_exit_code as _determine_exit_code,
)
from bioetl.interfaces.cli.commands.run_all_helpers import (
    filter_pipelines_by_provider as _filter_pipelines_by_provider,
)
from bioetl.interfaces.cli.commands.run_all_helpers import (
    get_available_providers as _get_available_providers,
)
from bioetl.interfaces.cli.commands.run_all_helpers import (
    validate_provider as _validate_provider,
)
from bioetl.interfaces.cli.commands.run_helpers import resolve_context_registry
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info
from bioetl.interfaces.cli.registry_helpers import (
    get_default_registry as _legacy_get_default_registry,
)

if TYPE_CHECKING:
    from bioetl.application.services import PipelineRunnerService


get_default_registry = _legacy_get_default_registry


async def _run_pipeline_async(
    service: PipelineRunnerService, pipeline: str, options: RunOptions
) -> RunResult:
    """Run a single pipeline asynchronously."""
    return await service.run(pipeline, options=options)


async def _run_pipelines_batch(
    service: PipelineRunnerService, pipelines: list[str], options: RunOptions
) -> BatchRunResult:
    """Run pipelines sequentially within a service context."""
    batch_result = BatchRunResult(total=len(pipelines))

    for pipeline in pipelines:
        try:
            result = await _run_pipeline_async(service, pipeline, options)
            if record_pipeline_result(
                batch_result=batch_result,
                pipeline=pipeline,
                result=result,
            ):
                break  # Stop processing remaining pipelines on shutdown
        except PipelineNotFoundError as e:
            record_pipeline_failure(
                batch_result=batch_result,
                pipeline=pipeline,
                title=f"[FAIL] {pipeline}: not found",
                detail=str(e),
            )
        except (BioETLError, OSError, RuntimeError, ValueError) as exc:
            error_msg = (
                f"{exc} (reason_code=CLI_RUN_ALL_PIPELINE_ERROR, "
                f"pipeline={pipeline}, error_type={type(exc).__name__})"
            )
            record_pipeline_failure(
                batch_result=batch_result,
                pipeline=pipeline,
                title=f"[FAIL] {pipeline}: unexpected error",
                detail=error_msg,
            )

    return batch_result


async def _run_all_pipelines_async(
    pipelines: list[str],
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    registry: PipelineRegistry | None = None,
) -> BatchRunResult:
    """Run all pipelines sequentially with optional health server.

    Args:
        pipelines: Ordered list of pipeline names to run sequentially.
        options: RunOptions controlling run type, limits, and filter settings.
        health_server_enabled: When True, starts the HTTP health server before
            pipeline execution. Defaults to True.
        health_port: TCP port the health server listens on. Defaults to
            DEFAULT_HEALTH_SERVER_PORT.

    Returns:
        BatchRunResult aggregating results from all pipeline runs.
    """
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    ensure_metrics_server_started()

    async with health_server_context(enabled=health_server_enabled, port=health_port):
        service = get_pipeline_runner_service(registry=registry)
        return await _run_pipelines_batch(service, pipelines, options)


def _echo_batch_summary(result: BatchRunResult, dry_run: bool) -> None:
    """Output batch run summary.

    Args:
        result: BatchRunResult with aggregate counts for the completed batch.
        dry_run: When True, prints a dry-run preview summary instead of execution stats.
    """
    _echo_batch_summary_impl(
        result=result,
        dry_run=dry_run,
        info_printer=echo_info,
        error_printer=echo_error,
    )


def _handle_destructive_confirmation(
    run_type: str, pipelines: list[str], dry_run: bool, yes: bool
) -> bool:
    """Handle confirmation for destructive operations.

    Args:
        run_type: Type of run; only 'rebuild' and 'backfill' trigger the confirmation
            prompt.
        pipelines: List of pipeline names that will be affected by the operation.
        dry_run: When True, skips the confirmation prompt.
        yes: When True, bypasses the interactive confirmation prompt.

    Returns:
        True if should continue, False if cancelled.
    """
    if not should_prompt_for_destructive_run(
        run_type=run_type,
        dry_run=dry_run,
        yes=yes,
    ):
        return True
    return _handle_destructive_confirmation_impl(
        run_type=run_type,
        pipelines=pipelines,
        dry_run=dry_run,
        yes=yes,
        confirm_fn=click.confirm,
        info_printer=echo_info,
        exit_func=sys.exit,
    )


def _handle_run_all_failure(
    exc: BaseException, *, source: str, reason_code: str
) -> None:
    """Handle run-all CLI failures with consistent error policy.

    Args:
        exc: Exception caught at the CLI command boundary.
        source: Provider name used as subject value in the structured error context.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_RUN_ALL_DOMAIN_ERROR').
    """
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="source",
        subject_value=source,
        domain_error_title="Batch execution failed with domain error",
        unexpected_error_title="Unexpected error during batch execution",
        interrupted_message="Batch run interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def _run_batch_with_policy(
    *,
    source: str,
    pipelines: list[str],
    options: RunOptions,
    health_server: bool,
    health_port: int,
    registry: PipelineRegistry | None = None,
) -> BatchRunResult | None:
    """Execute async batch run with typed exception policy.

    Args:
        source: Provider name used in error context for structured failure handling.
        pipelines: Ordered list of pipeline names to run sequentially.
        options: RunOptions controlling run type, limits, and filter settings.
        health_server: When True, enables the HTTP health server during execution.
        health_port: TCP port the health server listens on.

    Returns:
        BatchRunResult on success, None if an exception was handled and process will exit.
    """
    coro = _run_all_pipelines_async(
        pipelines,
        options,
        health_server_enabled=health_server,
        health_port=health_port,
        registry=registry,
    )
    try:
        return asyncio.run(coro)
    except PipelineNotFoundError as exc:
        _handle_run_all_failure(
            exc, source=source, reason_code="CLI_RUN_ALL_CONFIG_ERROR"
        )
    except BioETLError as exc:
        _handle_run_all_failure(
            exc, source=source, reason_code="CLI_RUN_ALL_DOMAIN_ERROR"
        )
    except KeyboardInterrupt as exc:
        _handle_run_all_failure(exc, source=source, reason_code="CLI_RUN_ALL_SIGINT")
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_run_all_failure(
            exc, source=source, reason_code="CLI_RUN_ALL_UNEXPECTED_ERROR"
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


@click.command("run-all")
@click.option(
    "--source", required=True, help="Provider name (e.g., chembl, pubchem, uniprot)"
)
@click.option(
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    default="incremental",
    help="Type of run for all pipelines",
)
@click.option("--limit", type=int, help="Maximum records per pipeline")
@click.option(
    "--dry-run", is_flag=True, help="Preview mode - show pipelines without execution"
)
@click.option(
    "--yes", "-y", is_flag=True, help="Skip confirmation prompt for rebuild/backfill"
)
@click.option(
    "--list-only",
    is_flag=True,
    help="List pipelines for the source without running them",
)
@click.option("--debug", is_flag=True, help="Enable DEBUG level logging")
@click.option(
    "--health-server/--no-health-server",
    "health_server",
    default=True,
    help="Enable/disable HTTP health server during execution.",
    show_default=True,
)
@click.option(
    "--health-port",
    type=int,
    default=DEFAULT_HEALTH_SERVER_PORT,
    help="Port for the HTTP health server.",
    show_default=True,
)
@click.pass_context
def run_all(
    ctx: click.Context,
    source: str,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    yes: bool,
    list_only: bool,
    debug: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Run all registered pipelines for one provider sequentially."""
    registry = resolve_context_registry(ctx)
    execution_plan, error_msg = create_run_all_execution_plan(
        source=source,
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        debug=debug,
        registry=registry,
    )
    if execution_plan is None:
        echo_error("Provider error", error_msg)
        sys.exit(ExitCode.FAIL)

    pipelines = execution_plan.pipelines

    if list_only:
        emit_run_all_listing(source=source, pipelines=pipelines)
        sys.exit(ExitCode.OK)

    _handle_destructive_confirmation(run_type, pipelines, dry_run, yes)

    emit_run_all_preview(
        source=source,
        pipelines=pipelines,
        dry_run=dry_run,
    )

    echo_health_server_info(health_server, health_port)

    batch_result = _run_batch_with_policy(
        source=source,
        pipelines=pipelines,
        options=execution_plan.options,
        health_server=health_server,
        health_port=health_port,
        registry=registry,
    )
    if batch_result is None:
        return

    _echo_batch_summary(batch_result, dry_run)
    sys.exit(_determine_exit_code(batch_result))


__all__ = [
    "BatchRunResult",
    "_determine_exit_code",
    "_filter_pipelines_by_provider",
    "_get_available_providers",
    "_validate_provider",
    "run_all",
]
