"""Canonical run-all command domain package."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.run_all import run_all as run_all

__all__ = ["run_all"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "run_all":
        raise AttributeError(name)

    return getattr(import_module("bioetl.interfaces.cli.commands.run_all"), name)
