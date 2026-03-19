"""Compatibility shim for run result presenter module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands._compat import reexport_module

reexport_module(
    __name__, "bioetl.interfaces.cli.commands.domains.run.result_presenter"
)
