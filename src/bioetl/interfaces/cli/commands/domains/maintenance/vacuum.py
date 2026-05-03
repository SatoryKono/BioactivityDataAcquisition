"""Internal wrapper for the public vacuum command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.vacuum import (
    get_lifecycle_service,
    get_vacuum_service,
    vacuum_all_command,
    vacuum_command,
)

__all__ = [
    "get_lifecycle_service",
    "get_vacuum_service",
    "vacuum_all_command",
    "vacuum_command",
]
