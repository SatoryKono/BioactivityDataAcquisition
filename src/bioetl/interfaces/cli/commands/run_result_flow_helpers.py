"""Compatibility support seam for run result-flow helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run.result_flow import (
        finalize_run_result as finalize_run_result,
    )
    from bioetl.interfaces.cli.commands.domains.run.result_flow import (
        present_run_health_info as present_run_health_info,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run.result_flow")
