"""Public archive command seam over the canonical maintenance module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.archive import (
        archive_command as archive_command,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.archive import (
        get_lifecycle_service as get_lifecycle_service,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.archive")
