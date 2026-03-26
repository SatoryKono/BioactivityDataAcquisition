"""Compatibility support seam for run-all command policy helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        RunAllCommandInput as RunAllCommandInput,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        build_run_all_command_input as build_run_all_command_input,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        exit_with_code as exit_with_code,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        handle_run_all_cli_failure as handle_run_all_cli_failure,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        prepare_run_all_execution_plan as prepare_run_all_execution_plan,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        run_all_command_flow as run_all_command_flow,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run_all.command_policy")
