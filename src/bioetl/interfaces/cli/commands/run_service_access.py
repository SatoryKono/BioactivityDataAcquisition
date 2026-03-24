"""Compatibility support seam for run service access."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run.service_access import (
        get_cli_run_orchestration_service as get_cli_run_orchestration_service,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run.service_access")
