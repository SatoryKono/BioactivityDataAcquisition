"""Public maintenance command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.command import (
        maintenance as maintenance,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.command")
