"""Canonical maintenance command domain package."""

from __future__ import annotations

from importlib import import_module

__all__ = ["maintenance"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "maintenance":
        raise AttributeError(name)

    module = import_module("bioetl.interfaces.cli.commands.maintenance")
    return module.maintenance
