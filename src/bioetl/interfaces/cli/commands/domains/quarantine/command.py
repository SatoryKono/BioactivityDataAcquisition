"""Internal wrapper for the public quarantine command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import click

    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _QuarantineRuntimeService,
        _QuarantineService,
    )

    get_quarantine_runtime_service: Callable[[str], _QuarantineRuntimeService]
    get_quarantine_service: Callable[[], _QuarantineService]
    quarantine: click.Group

install_public_module_alias(
    globals(),
    public_module="bioetl.interfaces.cli.commands.quarantine",
    exported_names=(
        "get_quarantine_runtime_service",
        "get_quarantine_service",
        "quarantine",
    ),
)
