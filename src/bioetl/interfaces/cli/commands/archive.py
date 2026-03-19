"""Public maintenance archive CLI entrypoint backed by the canonical module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands._compat import alias_module

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.archive")
