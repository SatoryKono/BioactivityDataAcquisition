"""Canonical run-all command domain package."""

from __future__ import annotations

__all__ = ["run_all"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "run_all":
        raise AttributeError(name)

    from bioetl.interfaces.cli.commands.domains.run_all.command import run_all

    return run_all
