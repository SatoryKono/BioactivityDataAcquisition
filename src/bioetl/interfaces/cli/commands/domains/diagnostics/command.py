"""Internal wrapper for the public diagnostics command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands.domains.shared.public_module_alias import (
    install_public_module_alias,
)

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.diagnostics import (
        COMMANDS as COMMANDS,
    )
    from bioetl.interfaces.cli.commands.diagnostics import (
        _build_diagnostics_guide_lines as _build_diagnostics_guide_lines,
    )
    from bioetl.interfaces.cli.commands.diagnostics import (
        diagnostics as diagnostics,
    )
    from bioetl.interfaces.cli.commands.diagnostics import (
        get_metrics_operator_profile as get_metrics_operator_profile,
    )
    from bioetl.interfaces.cli.commands.diagnostics import (
        get_observability_diagnostics_bundle as get_observability_diagnostics_bundle,
    )
    from bioetl.interfaces.cli.commands.diagnostics import (
        get_quarantine_runtime_service as get_quarantine_runtime_service,
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
