"""Public run-all command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run_all.command import (
        get_pipeline_runner_service as get_pipeline_runner_service,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.command import (
        run_all as run_all,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run_all.command")
