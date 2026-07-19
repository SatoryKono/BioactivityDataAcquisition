"""Internal wrapper for the public diagnostics command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import click

    from bioetl.composition.observability_api import (
        MetricsOperatorProfile,
        ObservabilityDiagnosticsBundle,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _QuarantineRuntimeService,
    )

    COMMANDS: tuple[str, ...]
    _build_diagnostics_guide_lines: Callable[[], list[str]]
    diagnostics: click.Group
    get_metrics_operator_profile: Callable[[], MetricsOperatorProfile]
    get_observability_diagnostics_bundle: Callable[[], ObservabilityDiagnosticsBundle]
    get_quarantine_runtime_service: Callable[[str], _QuarantineRuntimeService]

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
