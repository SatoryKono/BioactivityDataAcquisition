"""Support helpers for health-server integration helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        DEFAULT_HEALTH_SERVER_PORT as DEFAULT_HEALTH_SERVER_PORT,
    )
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        add_health_server_options as add_health_server_options,
    )
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        echo_health_server_info as echo_health_server_info,
    )
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        health_server_context as health_server_context,
    )

alias_module(
    __name__, "bioetl.interfaces.cli.commands.domains.health.server_integration"
)
