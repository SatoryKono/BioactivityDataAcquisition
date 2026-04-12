"""Canonical diagnostics command domain package."""

from __future__ import annotations

__all__ = ["diagnostics"]


def __getattr__(name: str) -> object:
    if name == "diagnostics":
        from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
            diagnostics,
        )

        return diagnostics
    raise AttributeError(name)
