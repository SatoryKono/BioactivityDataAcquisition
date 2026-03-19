"""Canonical maintenance command domain package."""

from __future__ import annotations

__all__ = ["maintenance"]


def __getattr__(name: str) -> object:
    if name == "maintenance":
        from bioetl.interfaces.cli.commands.domains.maintenance.command import (
            maintenance,
        )

        return maintenance
    raise AttributeError(name)
