"""Compatibility support seam for run command policy helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        execute_run_step as execute_run_step,
    )
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        finalize_run_step as finalize_run_step,
    )
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        handle_cli_failure as handle_cli_failure,
    )
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        handle_destructive_step as handle_destructive_step,
    )
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        map_status_to_exit_code as map_status_to_exit_code,
    )
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        prepare_run_request as prepare_run_request,
    )
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        RunCommandInput as RunCommandInput,
    )
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        run_command_flow as run_command_flow,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run.command_policy")
