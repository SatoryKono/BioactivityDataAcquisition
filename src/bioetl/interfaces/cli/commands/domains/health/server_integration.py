"""Health server integration for CLI commands.

Provides utilities for running the health server alongside long-running
pipeline operations. The health server exposes Kubernetes-compatible
health probes while pipelines execute.

This module follows the thin controller pattern - it delegates to
composition entrypoints for dependency injection.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)

if TYPE_CHECKING:
    from bioetl.interfaces.http.health_server import HealthServer


# Default port for health server during pipeline operations
DEFAULT_HEALTH_SERVER_PORT = 8081


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

    # Import here to avoid circular imports and keep interfaces layer clean
    from bioetl.composition.health_api import (
        get_health_server_dependencies,
        get_quarantine_service,
    )
    from bioetl.interfaces.http.health_server import HealthServer

    # Get dependencies from composition root (proper DI)
    deps = get_health_server_dependencies()
    try:
        quarantine_service = get_quarantine_service()
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
    "health_server_context",
]
