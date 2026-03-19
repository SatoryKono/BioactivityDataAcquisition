"""Compatibility shim for run command-policy module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands._compat import reexport_module

reexport_module(__name__, "bioetl.interfaces.cli.commands.domains.run.command_policy")
