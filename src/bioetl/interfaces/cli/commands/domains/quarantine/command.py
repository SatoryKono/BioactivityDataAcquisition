"""Internal wrapper for the public quarantine command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
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
