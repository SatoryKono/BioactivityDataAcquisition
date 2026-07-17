"""Internal wrapper for the public quarantine command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
)

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.quarantine import (
        get_quarantine_runtime_service as get_quarantine_runtime_service,
    )
    from bioetl.interfaces.cli.commands.quarantine import (
        get_quarantine_service as get_quarantine_service,
    )
    from bioetl.interfaces.cli.commands.quarantine import (
        quarantine as quarantine,
    )

install_public_module_alias(
    globals(),
    public_module="bioetl.interfaces.cli.commands.quarantine",
    exported_names=(
        "get_quarantine_runtime_service",
        "get_quarantine_service",
        "quarantine",
    ),
)
