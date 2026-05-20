"""Canonical composite-run command domain package."""

from __future__ import annotations

__all__ = ["run_composite"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "run_composite":
        raise AttributeError(name)

    from bioetl.interfaces.cli.commands.domains.composite.command import (
        run_composite,
    )

    return run_composite
