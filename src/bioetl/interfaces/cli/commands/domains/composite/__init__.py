"""Canonical composite-run command domain package."""

from __future__ import annotations

from importlib import import_module

__all__ = ["run_composite"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "run_composite":
        raise AttributeError(name)

    return import_module("bioetl.interfaces.cli.commands.run_composite").run_composite
