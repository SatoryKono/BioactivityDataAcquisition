"""Canonical diagnostics command domain package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
        diagnostics as diagnostics,
    )

__all__ = ["diagnostics"]


def __getattr__(name: str) -> object:
    if name != "diagnostics":
        raise AttributeError(name)
    from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
        diagnostics,
    )

    return diagnostics
