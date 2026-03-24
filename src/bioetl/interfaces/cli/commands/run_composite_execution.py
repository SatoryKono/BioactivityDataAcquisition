"""Compatibility support seam for run-composite execution helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import (
        CompositeRuntimeConfig as CompositeRuntimeConfig,
    )
    from bioetl.interfaces.cli.commands.domains.composite.execution import (
        bootstrap_composite_runner as bootstrap_composite_runner,
    )
    from bioetl.interfaces.cli.commands.domains.composite.execution import (
        build_run_composite_result as build_run_composite_result,
    )
    from bioetl.interfaces.cli.commands.domains.composite.execution import (
        load_composite_config as load_composite_config,
    )
    from bioetl.interfaces.cli.commands.domains.composite.execution import (
        run_composite_async as run_composite_async,
    )
    from bioetl.interfaces.cli.commands.domains.composite.execution import (
        run_composite_inner as run_composite_inner,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.composite.execution")
