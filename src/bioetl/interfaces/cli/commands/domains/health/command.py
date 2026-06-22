"""Internal wrapper for the public health command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
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
