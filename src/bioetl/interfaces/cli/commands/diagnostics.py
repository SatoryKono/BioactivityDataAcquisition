"""Retained public diagnostics command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
        diagnostics as diagnostics,
    )
    from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
        get_observability_diagnostics_bundle as get_observability_diagnostics_bundle,
    )
    from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
        get_quarantine_manager as get_quarantine_manager,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.diagnostics.command")
