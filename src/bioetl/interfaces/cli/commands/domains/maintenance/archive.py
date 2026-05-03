"""Internal wrapper for the public archive command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.archive import (
    archive_command,
    get_lifecycle_service,
)

__all__ = ["archive_command", "get_lifecycle_service"]
