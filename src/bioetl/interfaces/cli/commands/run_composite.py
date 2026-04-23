"""Public run-composite command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.interfaces.cli.commands.domains.composite.command import (
        bootstrap_composite_runner as bootstrap_composite_runner,
    )
    from bioetl.interfaces.cli.commands.domains.composite.command import (
        load_composite_config as load_composite_config,
    )
    from bioetl.interfaces.cli.commands.domains.composite.command import (
        run_composite as run_composite,
    )

    _CompositeRuntimeConfigType = CompositeRuntimeConfig

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.composite.command")
