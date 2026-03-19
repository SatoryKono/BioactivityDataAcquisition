"""Canonical quarantine command domain package."""

from __future__ import annotations

__all__ = ["quarantine"]


def __getattr__(name: str) -> object:
    if name == "quarantine":
        from bioetl.interfaces.cli.commands.domains.quarantine.command import quarantine

        return quarantine
    raise AttributeError(name)
