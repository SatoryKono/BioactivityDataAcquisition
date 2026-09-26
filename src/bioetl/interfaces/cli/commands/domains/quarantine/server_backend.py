"""Quarantine-owned wrapper for the long-lived explorer backend."""

from __future__ import annotations

from pathlib import Path

DEFAULT_QUARANTINE_SERVER_PORT = 8000

__all__ = [
    "DEFAULT_QUARANTINE_SERVER_PORT",
    "run_long_lived_quarantine_backend_command",
]


def run_long_lived_quarantine_backend_command(
    *,
    host: str,
    port: int,
    data_root: Path | None = None,
) -> None:
    """Start the shared long-lived backend used by the quarantine explorer."""
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        run_long_lived_health_server_command,
    )

    if data_root is None:
        run_long_lived_health_server_command(
            host=host,
            port=port,
            start_metrics=False,
        )
    else:
        run_long_lived_health_server_command(
            host=host,
            port=port,
            start_metrics=False,
            data_root=data_root,
        )
