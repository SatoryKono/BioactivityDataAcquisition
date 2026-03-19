"""Compatibility shim aliasing the canonical health-server module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands._compat import alias_module

alias_module(
    __name__, "bioetl.interfaces.cli.commands.domains.health.server_integration"
)
