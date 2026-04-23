"""Public quarantine command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.quarantine.command import (
        get_quarantine_manager as get_quarantine_manager,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.command import (
        get_quarantine_service as get_quarantine_service,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.command import (
        quarantine as quarantine,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.quarantine.command")
