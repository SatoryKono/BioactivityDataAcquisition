"""Internal wrapper for the public health command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
)

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.health import (
        get_health_server_dependencies as get_health_server_dependencies,
    )
    from bioetl.interfaces.cli.commands.health import (
        get_health_service as get_health_service,
    )
    from bioetl.interfaces.cli.commands.health import (
        health as health,
    )
    from bioetl.interfaces.cli.commands.health import (
        health_check as health_check,
    )
    from bioetl.interfaces.cli.commands.health import (
        health_server_command as health_server_command,
    )

install_public_module_alias(
    globals(),
    public_module="bioetl.interfaces.cli.commands.health",
    exported_names=(
        "get_health_server_dependencies",
        "get_health_service",
        "health",
        "health_check",
        "health_server_command",
    ),
)
