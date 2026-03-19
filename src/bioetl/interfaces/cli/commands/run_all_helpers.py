"""Public run-all helper seam backed by the canonical domain module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands._compat import alias_module

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run_all.support")
