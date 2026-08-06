"""Helper functions for the run-composite CLI command."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable, Coroutine

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
    map_success_flag_to_exit_code,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

__all__ = [
    "emit_composite_startup",
    "exit_with_composite_result",
    "handle_run_composite_exception",
    "run_composite_with_cli_policy",
]


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    pipeline_name: str | None = None,
) -> bool:
    """Push metrics without turning a completed CLI run into failure."""
    from bioetl.interfaces.cli.commands.domains.health.metrics_publication_integration import (
        publish_metrics_safely,
    )

    # Best-effort only: never raise into composite finally / SystemExit paths.
    return publish_metrics_safely(
        run_label=run_label,
        pipeline_name=pipeline_name,
    )


def emit_composite_startup(
    *,
    composite: str,
    dry_run: bool,
    resume: bool,
    cached_bronze_enabled: bool,
    health_server: bool,
    health_port: int,
    info_printer: Callable[[str], None] = echo_info,
    warning_printer: Callable[[str], None] = echo_warning,
    health_info_printer: Callable[[bool, int], None] = echo_health_server_info,
) -> None:
    """Emit startup information for composite execution."""
    info_printer(f"Starting composite pipeline: {composite}")
    if dry_run:
        warning_printer("Dry-run mode: no data will be written")
    if resume:
        info_printer("Resume mode: continuing from last checkpoint")
    if cached_bronze_enabled:
        warning_printer(
            "Composite execution is outside the strict exact-replay boundary. "
            "Cached Bronze is rebuild/resume evidence only; strict exact replay "
            "remains source-run only."
        )
    health_info_printer(health_server, health_port)


def handle_run_composite_exception(
    exc: BaseException,
    *,
    composite: str,
    reason_code: str,
) -> None:
    """Render a canonical CLI failure for run-composite."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="composite",
        subject_value=composite,
        domain_error_title="Composite execution failed with domain error",
        unexpected_error_title="Unexpected error during composite execution",
        interrupted_message="Composite pipeline interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def run_composite_with_cli_policy(
    *,
    composite: str,
    runtime: CompositeRuntimeConfig,
    health_server: bool,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    run_async: Callable[
        [str, CompositeRuntimeConfig, bool, int],
        Coroutine[object, object, tuple[bool, str | None]],
    ],
    exception_handler: Callable[[BaseException, str, str], None] | None = None,
) -> tuple[bool, str | None]:
    """Execute run-composite coroutine with shared CLI exception policy."""
    coro = run_async(
        composite,
        runtime,
        health_server,
        health_port,
    )
    success = False
    error_message: str | None = None
    handler = exception_handler or _default_exception_handler
    try:
        success, error_message = asyncio.run(coro)
    except BioETLError as exc:
        handler(exc, composite, "CLI_COMPOSITE_DOMAIN_ERROR")
    except KeyboardInterrupt as exc:
        handler(exc, composite, "CLI_COMPOSITE_SIGINT")
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        handler(exc, composite, "CLI_COMPOSITE_UNEXPECTED_ERROR")
    finally:
        # Best-effort metrics: never replace SystemExit/result from the handler.
        push_metrics_to_gateway(pipeline_name=f"composite_{composite}")
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return success, error_message


def exit_with_composite_result(success: bool, error_message: str | None) -> None:
    """Exit the CLI process using the canonical run-composite result mapping."""
    exit_code = map_success_flag_to_exit_code(success)
    if success:
        echo_info("Composite pipeline completed successfully")
        sys.exit(exit_code)
    echo_error("Composite pipeline failed", error_message or "Unknown error")
    sys.exit(exit_code)


def _default_exception_handler(
    exc: BaseException,
    composite: str,
    reason_code: str,
) -> None:
    handle_run_composite_exception(
        exc,
        composite=composite,
        reason_code=reason_code,
    )
