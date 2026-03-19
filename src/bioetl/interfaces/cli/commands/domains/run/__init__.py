"""Canonical run-command domain package."""

from __future__ import annotations

__all__ = ["run"]


def __getattr__(name: str) -> object:
    if name == "run":
        from bioetl.interfaces.cli.commands.domains.run.command import run

        return run
    raise AttributeError(name)
