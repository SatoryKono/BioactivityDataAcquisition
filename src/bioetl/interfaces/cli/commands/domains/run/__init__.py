"""Canonical run-command domain package."""

from __future__ import annotations

__all__ = ["run"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "run":
        raise AttributeError(name)

    from bioetl.interfaces.cli.commands.run import run

    return run
