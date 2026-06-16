"""Health server integration for CLI commands.

Provides utilities for running the health server alongside long-running
pipeline operations. The health server exposes Kubernetes-compatible
health probes while pipelines execute.

This module follows the thin controller pattern - it delegates to
composition entrypoints for dependency injection.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, cast

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    build_health_server_info_lines,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

if TYPE_CHECKING:
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition.health_api import (
        HealthServerDependenciesProtocol,
        QuarantineRuntimeServiceProtocol,
        RuntimeSettingsProtocol,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.interfaces.http.health_server import HealthServer


# Default port for health server during pipeline operations
DEFAULT_HEALTH_SERVER_PORT = 8081

_HEALTH_SERVER_DOMAIN_ERROR_TITLE = "Health server failed with domain error"
_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE = "Unexpected error in health server command"
_HEALTH_SERVER_INTERRUPTED_MESSAGE = "Health server interrupted by user (Ctrl+C)"


def get_health_server_dependencies() -> HealthServerDependenciesProtocol:
    """Load health-listener dependencies from the canonical composition seam."""
    from bioetl.composition.health_api import get_health_server_dependencies as _impl

    return _impl()


def get_health_server_quarantine_service() -> QuarantineService:
    """Load read-only quarantine service for health listener endpoints."""
    from bioetl.composition.health_api import get_quarantine_service as _impl

    return _impl()


def get_quarantine_runtime_service(
    pipeline: str,
) -> QuarantineRuntimeServiceProtocol:
    """Load one pipeline-scoped quarantine runtime service from composition."""
    from bioetl.composition.health_api import get_quarantine_runtime_service as _impl

    return cast("QuarantineRuntimeServiceProtocol", _impl(pipeline))


def get_runtime_settings() -> RuntimeSettingsProtocol:
    """Load runtime settings through the composition boundary."""
    from bioetl.composition.health_api import get_runtime_settings as _impl

    return cast("RuntimeSettingsProtocol", _impl())


def _start_metrics_server_via_interface(
    *,
    port: int,
    addr: str,
    fail_fast: bool,
    retry_count: int,
    retry_delay: float,
    logger: LoggerPort | None,
) -> bool:
    """Start the metrics server through the observability composition seam."""
    from bioetl.composition.observability_api import start_metrics_server as _impl

    return _impl(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


# Backward-compatible patch point for existing tests and callers.
start_metrics_server = _start_metrics_server_via_interface


def get_metrics_server_starter() -> Callable[..., bool]:
    """Expose the patchable metrics-server starter without direct call-site drift."""
    return start_metrics_server


def _handle_health_failure(
    exc: BaseException,
    *,
    reason_code: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
) -> None:
    """Handle health command failures with the shared CLI execution policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="target",
        subject_value=target,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


def _echo_health_server_startup(host: str, port: int) -> None:
    """Print startup information for the long-lived health server command."""
    for line in build_health_server_info_lines(host, port):
        click.echo(line)


def build_health_server_pycache_prefix() -> Path:
    """Return the deterministic pycache root for the health server process."""
    return Path(tempfile.gettempdir()) / "bioetl-pycache"


def _start_health_observability(logger: LoggerPort | None = None) -> None:
    """Start the Prometheus metrics server for long-lived health mode."""
    settings = get_runtime_settings()
    if not (
        settings.observability.metrics_enabled
        and settings.observability.metrics_server_enabled
    ):
        if logger is not None:
            logger.info(
                "health_server_metrics_disabled",
                metrics_enabled=settings.observability.metrics_enabled,
                metrics_server_enabled=settings.observability.metrics_server_enabled,
            )
        return

    started = get_metrics_server_starter()(
        port=settings.metrics_port,
        addr=settings.metrics_addr,
        fail_fast=settings.observability.metrics_fail_fast,
        retry_count=settings.observability.metrics_retry_count,
        retry_delay=settings.observability.metrics_retry_delay,
        logger=logger,
    )
    if logger is not None:
        logger.info(
            "health_server_metrics_ready",
            metrics_started=started,
            metrics_port=settings.metrics_port,
            metrics_addr=settings.metrics_addr,
        )


async def _run_health_server(host: str, port: int) -> None:
    """Start and keep the health server alive until interrupted."""
    from bioetl.interfaces.http.health_server import HealthServer

    if sys.pycache_prefix is None:
        sys.pycache_prefix = str(build_health_server_pycache_prefix())
    deps = get_health_server_dependencies()
    _start_health_observability()
    quarantine_service: QuarantineService | None = None
    try:
        quarantine_service = get_health_server_quarantine_service()
    except CLI_ENTRYPOINT_TYPED_ERRORS:
        # Why: Health probes must stay available even when quarantine storage
        # setup fails; explorer endpoints remain disabled in that case.
        quarantine_service = None
    server = HealthServer(
        host=host,
        port=port,
        health_monitor=deps.health_monitor,
        quarantine_service=quarantine_service,
        checkpoint_port=deps.checkpoint_port,
        run_manifest_port=deps.run_manifest_port,
        run_ledger_port=deps.run_ledger_port,
    )
    try:
        await server.start()
        while True:
            await asyncio.sleep(1)
    finally:
        await server.stop()
        await deps.checkpoint_port.aclose()
        if quarantine_service is not None:
            await quarantine_service.aclose()
        click.echo("\nHealth server stopped.")


def run_long_lived_health_server_command(host: str, port: int) -> None:
    """Start the long-lived health/quarantine explorer backend."""
    _echo_health_server_startup(host, port)
    coro = _run_health_server(host=host, port=port)
    try:
        asyncio.run(coro)
    except asyncio.CancelledError:
        return
    except BioETLError as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_SERVER_DOMAIN_ERROR",
            target=f"{host}:{port}",
            domain_error_title=_HEALTH_SERVER_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_HEALTH_SERVER_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_SERVER_UNEXPECTED_ERROR",
            target=f"{host}:{port}",
            domain_error_title=_HEALTH_SERVER_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_HEALTH_SERVER_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        sys.exit(ExitCode.OK)
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


@asynccontextmanager
async def health_server_context(
    enabled: bool,
    host: str = "127.0.0.1",
    port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> AsyncIterator[HealthServer | None]:
    """Run health server for the context lifetime when enabled.

    Yields the running HealthServer for the duration of the async context,
    then stops it on exit. If the server fails to bind (port in use), a
    warning is printed and None is yielded so the pipeline continues.

    Args:
        enabled: When False, yields None immediately without starting a server.
        host: IP address to bind to. Defaults to localhost.
        port: TCP port to listen on. Defaults to DEFAULT_HEALTH_SERVER_PORT.
    """
    if not enabled:
        yield None
        return

    from bioetl.interfaces.http.health_server import HealthServer

    # Get dependencies from composition root (proper DI)
    deps = get_health_server_dependencies()
    try:
        quarantine_service = get_health_server_quarantine_service()
    except CLI_ENTRYPOINT_TYPED_ERRORS:
        # Why: keep health probes available during pipeline runs even if
        # quarantine explorer dependencies are temporarily unavailable.
        quarantine_service = None
    server = HealthServer(
        host=host,
        port=port,
        health_monitor=deps.health_monitor,
        quarantine_service=quarantine_service,
        checkpoint_port=deps.checkpoint_port,
        run_manifest_port=deps.run_manifest_port,
        run_ledger_port=deps.run_ledger_port,
    )

    try:
        await server.start()
    except OSError:
        await deps.checkpoint_port.aclose()
        if quarantine_service is not None:
            await quarantine_service.aclose()
        click.echo(
            f"Warning: Health server failed to bind to {host}:{port} "
            f"(port in use). Pipeline will continue without health server.",
            err=True,
        )
        yield None
        return

    try:
        yield server
    finally:
        await server.stop()
        await deps.checkpoint_port.aclose()
        if quarantine_service is not None:
            await quarantine_service.aclose()


def add_health_server_options(cmd: click.Command) -> click.Command:
    """Add health server options to a Click command.

    Adds --health-server/--no-health-server and --health-port options
    to the given command.

    Args:
        cmd: Click command to add options to.

    Returns:
        Modified command with health server options.
    """
    cmd = click.option(
        "--health-server/--no-health-server",
        default=True,
        help="Enable/disable HTTP health server during execution (default: enabled).",
        show_default=True,
    )(cmd)

    cmd = click.option(
        "--health-port",
        type=int,
        default=DEFAULT_HEALTH_SERVER_PORT,
        help="Port for the HTTP health server.",
        show_default=True,
    )(cmd)

    return cmd


def echo_health_server_info(enabled: bool, port: int, host: str = "127.0.0.1") -> None:
    """Output health server status information.

    Args:
        enabled: Whether health server is enabled.
        port: Port the server is listening on.
        host: Host the server is bound to (default: 127.0.0.1 for security).
    """
    if enabled:
        click.echo(f"Health server: http://{host}:{port}/health")


COMMANDS = (add_health_server_options, echo_health_server_info, health_server_context)

__all__ = [
    "DEFAULT_HEALTH_SERVER_PORT",
    "add_health_server_options",
    "echo_health_server_info",
    "get_health_server_dependencies",
    "get_health_server_quarantine_service",
    "get_quarantine_runtime_service",
    "get_runtime_settings",
    "health_server_context",
    "run_long_lived_health_server_command",
    "start_metrics_server",
]
