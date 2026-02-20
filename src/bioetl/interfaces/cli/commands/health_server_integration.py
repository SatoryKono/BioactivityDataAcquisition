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
    """Context manager that optionally runs a health server.

    When enabled, starts an HTTP health server before yielding and
    gracefully shuts it down afterward. Provides Kubernetes-compatible
    liveness and readiness probes.

    Args:
        enabled: Whether to start the health server.
        host: Host to bind the server to.
        port: Port for the health server.

    Yields:
        HealthServer instance if enabled, None otherwise.

    Example:
        async with health_server_context(enabled=True, port=DEFAULT_HEALTH_SERVER_PORT) as server:
            # Health server is running
            await run_pipeline()
        # Health server is stopped
    """
    if not enabled:
        yield None
        return

    # Import here to avoid circular imports and keep interfaces layer clean
    from bioetl.composition.entrypoints import get_health_server_dependencies
    from bioetl.interfaces.http.health_server import HealthServer

    # Get dependencies from composition root (proper DI)
    deps = get_health_server_dependencies()

    server = HealthServer(
        host=host,
        port=port,
        health_monitor=deps.health_monitor,
        logger=deps.logger if hasattr(deps, "logger") else None,
    )

    try:
        await server.start()
        yield server
    finally:
        await server.stop()


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
