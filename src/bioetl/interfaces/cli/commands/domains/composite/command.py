"""Internal wrapper for the public run-composite command module."""

from __future__ import annotations

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
)

install_public_module_alias(
    globals(),
    public_module="bioetl.interfaces.cli.commands.run_composite",
    exported_names=(
        "bootstrap_composite_runner",
        "load_composite_config",
        "run_composite",
    ),
)

__all__ = [
    "CompositeRuntimeConfig",
    "bootstrap_composite_runner",
    "load_composite_config",
    "run_composite",
]
