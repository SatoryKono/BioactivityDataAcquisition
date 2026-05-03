"""Internal wrapper for the public quarantine command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.quarantine import (
    get_quarantine_runtime_service,
    get_quarantine_service,
    quarantine,
)

__all__ = [
    "get_quarantine_runtime_service",
    "get_quarantine_service",
    "quarantine",
]
