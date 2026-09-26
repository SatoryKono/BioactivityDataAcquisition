"""Click option and echo helpers for the health server CLI surface."""

from __future__ import annotations

import click

from bioetl.interfaces.cli.commands.domains.health.server_integration_lifecycle import (
    DEFAULT_HEALTH_SERVER_PORT,
    health_server_context,
)


def add_health_server_options(cmd: click.Command) -> click.Command:
    """Add health server options to a Click command."""
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
    """Output health server status information."""
    if enabled:
        click.echo(f"Health server: http://{host}:{port}/health")


COMMANDS = (add_health_server_options, echo_health_server_info, health_server_context)

__all__ = [
    "COMMANDS",
    "add_health_server_options",
    "echo_health_server_info",
]
