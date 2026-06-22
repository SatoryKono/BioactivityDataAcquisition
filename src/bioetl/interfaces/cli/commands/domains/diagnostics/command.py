"""Internal wrapper for the public diagnostics command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
)

install_public_module_alias(
    globals(),
    public_module="bioetl.interfaces.cli.commands.diagnostics",
    exported_names=(
        "COMMANDS",
        "_build_diagnostics_guide_lines",
        "diagnostics",
        "get_metrics_operator_profile",
        "get_observability_diagnostics_bundle",
        "get_quarantine_runtime_service",
    ),
)
