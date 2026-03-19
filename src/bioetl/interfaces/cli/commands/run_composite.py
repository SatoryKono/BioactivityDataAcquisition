"""Compatibility shim aliasing the canonical run-composite command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    # from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_models import (
        CompositeRuntimeConfig,  # noqa: F401
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.composite.command")
