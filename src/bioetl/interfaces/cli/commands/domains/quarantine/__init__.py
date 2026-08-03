"""Canonical quarantine command domain package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.quarantine.command import (
        quarantine as quarantine,
    )

__all__ = ["quarantine"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "quarantine":
        raise AttributeError(name)

    from bioetl.interfaces.cli.commands.domains.quarantine.command import quarantine

    return quarantine
