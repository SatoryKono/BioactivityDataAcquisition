"""Owner package for composition bootstrap modules.

The package remains importable so ``bioetl.composition.bootstrap.*`` owner modules
keep a stable namespace, but first-party callers must import concrete owner modules
directly instead of relying on package-root re-exports.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.context import PipelineRunContext

__all__: list[str] = []


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Compatibility package-root alias for runtime pipeline bootstrap."""
    module = import_module("bioetl.composition.bootstrap.runtime.pipeline")
    impl = module.bootstrap_pipeline_runner
    return impl(ctx, registry=registry)
