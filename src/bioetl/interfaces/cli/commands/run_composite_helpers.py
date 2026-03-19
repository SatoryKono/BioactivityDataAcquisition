"""Public run-composite helper seam backed by the canonical domain module."""

from __future__ import annotations

# from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.composite.runtime_models import (
    CompositeRuntimeConfig,  # noqa: F401
)
from bioetl.interfaces.cli.commands._compat import alias_module

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.composite.support")
