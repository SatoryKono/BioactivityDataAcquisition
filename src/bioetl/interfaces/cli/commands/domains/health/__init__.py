"""Canonical health command domain package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.health.command import health as health

__all__ = ["health"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "health":
        raise AttributeError(name)

    from bioetl.interfaces.cli.commands.domains.health.command import health

    return health
