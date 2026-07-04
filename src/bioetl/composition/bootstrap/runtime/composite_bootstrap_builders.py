"""Internal builder helpers for composite runtime bootstrap.

This module holds orchestration internals so ``composite.py`` can remain
as a thin compatibility facade with stable patch points.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime.runner_assembly import (
    create_composite_runner,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    bootstrap_runtime_basics,
    build_runner_factories,
    build_support_services,
)

__all__ = [
    "bootstrap_runtime_basics",
    "build_runner_factories",
    "build_support_services",
    "create_composite_runner",
]

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig

    # Preserve the stable runtime-config facade in this module's type surface.
    RuntimeConfig = CompositeRuntimeConfig
