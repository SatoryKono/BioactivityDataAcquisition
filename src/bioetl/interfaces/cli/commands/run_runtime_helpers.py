"""Compatibility support seam for run runtime helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
        build_run_command_input as build_run_command_input,
    )
    from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
        build_run_pipeline_callable as build_run_pipeline_callable,
    )
    from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
        run_pipeline_async as run_pipeline_async,
    )
    from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
        run_prepared_request_async as run_prepared_request_async,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run.runtime_helpers")
