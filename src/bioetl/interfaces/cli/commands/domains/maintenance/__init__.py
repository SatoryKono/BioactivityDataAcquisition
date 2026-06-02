"""Canonical maintenance command domain package."""

from __future__ import annotations

__all__ = ["maintenance"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "maintenance":
        raise AttributeError(name)

    from bioetl.interfaces.cli.commands.maintenance import maintenance

    return maintenance
