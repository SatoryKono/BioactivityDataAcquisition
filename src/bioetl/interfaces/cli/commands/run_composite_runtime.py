"""Compatibility support seam for run-composite runtime helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.interfaces.cli.commands.domains.composite.runtime import (
        build_runtime_config as build_runtime_config,
    )
    from bioetl.interfaces.cli.commands.domains.composite.runtime import (
        echo_composite_startup as echo_composite_startup,
    )
    from bioetl.interfaces.cli.commands.domains.composite.runtime import (
        parse_enrich_only as parse_enrich_only,
    )

    _CompositeRuntimeConfigType = CompositeRuntimeConfig

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.composite.runtime")
