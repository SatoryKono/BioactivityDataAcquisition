"""Compatibility support seam for run-composite helper utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.interfaces.cli.commands.domains.composite.support import (
        emit_composite_startup as emit_composite_startup,
    )
    from bioetl.interfaces.cli.commands.domains.composite.support import (
        exit_with_composite_result as exit_with_composite_result,
    )
    from bioetl.interfaces.cli.commands.domains.composite.support import (
        handle_run_composite_exception as handle_run_composite_exception,
    )
    from bioetl.interfaces.cli.commands.domains.composite.support import (
        push_metrics_to_gateway as push_metrics_to_gateway,
    )
    from bioetl.interfaces.cli.commands.domains.composite.support import (
        run_composite_with_cli_policy as run_composite_with_cli_policy,
    )

    _CompositeRuntimeConfigType = CompositeRuntimeConfig

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.composite.support")
