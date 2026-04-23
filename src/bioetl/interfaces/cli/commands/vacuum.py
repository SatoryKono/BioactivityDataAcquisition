"""Public vacuum command seam over the canonical maintenance module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
        get_lifecycle_service as get_lifecycle_service,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
        get_vacuum_service as get_vacuum_service,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
        vacuum_all_command as vacuum_all_command,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
        vacuum_command as vacuum_command,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.vacuum")
