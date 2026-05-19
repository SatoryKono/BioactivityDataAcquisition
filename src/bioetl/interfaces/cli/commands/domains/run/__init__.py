"""Canonical run-command domain package."""

from __future__ import annotations

__all__ = ["run"]


def __getattr__(name: str) -> object:
    if name == "run":
        from bioetl.interfaces.cli.commands.run import run

        return run
    raise AttributeError(name)
