"""Compatibility support seam for shared CLI execution policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
        CLI_ENTRYPOINT_TYPED_ERRORS as CLI_ENTRYPOINT_TYPED_ERRORS,
    )
    from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
        BatchRunResultProtocol as BatchRunResultProtocol,
    )
    from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
        build_failure_context as build_failure_context,
    )
    from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
        handle_cli_failure as handle_cli_failure,
    )
    from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
        map_batch_run_result_to_exit_code as map_batch_run_result_to_exit_code,
    )
    from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
        map_run_status_to_exit_code as map_run_status_to_exit_code,
    )
    from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
        map_success_flag_to_exit_code as map_success_flag_to_exit_code,
    )
    from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
        render_failure_context as render_failure_context,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.shared.execution_policy")
