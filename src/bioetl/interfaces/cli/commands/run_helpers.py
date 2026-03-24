"""Compatibility support seam for run helper utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run.support import (
        get_runner_logger as get_runner_logger,
    )
    from bioetl.interfaces.cli.commands.domains.run.support import (
        handle_destructive_run_confirmation as handle_destructive_run_confirmation,
    )
    from bioetl.interfaces.cli.commands.domains.run.support import (
        resolve_context_registry as resolve_context_registry,
    )
    from bioetl.interfaces.cli.commands.domains.run.support import (
        show_cleanup_preview as show_cleanup_preview,
    )
    from bioetl.interfaces.cli.commands.domains.run.support import (
        validate_pipeline_name as validate_pipeline_name,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run.support")
