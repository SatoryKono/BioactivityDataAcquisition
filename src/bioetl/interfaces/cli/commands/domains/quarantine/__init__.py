"""Canonical quarantine command domain package."""

from __future__ import annotations

__all__ = ["quarantine"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "quarantine":
        raise AttributeError(name)

    from bioetl.interfaces.cli.commands.domains.quarantine.command import quarantine

    return quarantine
