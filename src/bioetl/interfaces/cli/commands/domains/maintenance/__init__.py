"""Canonical maintenance command domain package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from click.core import Group

    maintenance: Group

__all__ = ["maintenance"]


def __getattr__(name: str) -> object:
    """Resolve retained command exports lazily to avoid import cycles."""
    if name != "maintenance":
        raise AttributeError(name)

    from bioetl.interfaces.cli.commands.domains.maintenance.command_group import (
        maintenance as command,
    )

    return command
