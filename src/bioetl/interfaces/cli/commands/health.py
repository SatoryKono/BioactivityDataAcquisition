"""Public health command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.health.command import (
        get_health_server_dependencies as get_health_server_dependencies,
    )
    from bioetl.interfaces.cli.commands.domains.health.command import (
        get_health_service as get_health_service,
    )
    from bioetl.interfaces.cli.commands.domains.health.command import (
        health as health,
    )
    from bioetl.interfaces.cli.commands.domains.health.command import (
        health_check as health_check,
    )
    from bioetl.interfaces.cli.commands.domains.health.command import (
        health_server_command as health_server_command,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.health.command")
