"""Quarantine-owned wrapper for the long-lived explorer backend."""

from __future__ import annotations

DEFAULT_QUARANTINE_SERVER_PORT = 8081

__all__ = [
    "DEFAULT_QUARANTINE_SERVER_PORT",
    "run_long_lived_quarantine_backend_command",
]


def run_long_lived_quarantine_backend_command(*, host: str, port: int) -> None:
    """Start the shared long-lived backend used by the quarantine explorer."""
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        run_long_lived_health_server_command,
    )

    run_long_lived_health_server_command(host=host, port=port)
