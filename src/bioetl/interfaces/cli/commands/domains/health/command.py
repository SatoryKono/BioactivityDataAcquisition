"""Internal wrapper for the public health command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import click

    from bioetl.application.services.health_service import HealthService
    from bioetl.composition.health_service_access import HealthServerDependencies

    get_health_server_dependencies: Callable[[], HealthServerDependencies]
    get_health_service: Callable[[], HealthService]
    health: click.Group
    health_check: click.Command
    health_server_command: click.Command

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
