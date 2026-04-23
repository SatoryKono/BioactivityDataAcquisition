"""Public run command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run.command import (
        build_run_options as build_run_options,
    )
    from bioetl.interfaces.cli.commands.domains.run.command import (
        execute_run as execute_run,
    )
    from bioetl.interfaces.cli.commands.domains.run.command import (
        get_cli_run_orchestration_service as get_cli_run_orchestration_service,
    )
    from bioetl.interfaces.cli.commands.domains.run.command import (
        handle_cli_failure as handle_cli_failure,
    )
    from bioetl.interfaces.cli.commands.domains.run.command import run as run
    from bioetl.interfaces.cli.commands.domains.run.command import (
        validate_options as validate_options,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run.command")
