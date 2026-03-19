"""Canonical health command domain package."""

from __future__ import annotations

__all__ = ["health"]


def __getattr__(name: str) -> object:
    if name == "health":
        from bioetl.interfaces.cli.commands.domains.health.command import health

        return health
    raise AttributeError(name)
