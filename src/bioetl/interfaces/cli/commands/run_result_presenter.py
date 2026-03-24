"""Compatibility support seam for run result presentation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run.result_presenter import (
        echo_run_result as echo_run_result,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run.result_presenter")
