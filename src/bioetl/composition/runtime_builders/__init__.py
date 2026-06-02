"""Leaf runtime builders used by composition factories and bootstrap wrappers."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.composition.runtime_builders.ledger_collaborator import (
        PipelineRunnerProtocol,
    )
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerBuilderWiring,
    )
    from bioetl.domain.context import PipelineRunContext

if TYPE_CHECKING:

    def build_pipeline_runner(
        ctx: PipelineRunContext,
        registry: PipelineRegistry | None = None,
        *,
        wiring: RunnerBuilderWiring | None = ...,
    ) -> PipelineRunnerProtocol: ...

else:

    def build_pipeline_runner(*args: object, **kwargs: object) -> object:
        """Lazily dispatch to the concrete runner builder without package import cycles."""
        from bioetl.composition.runtime_builders.runner_builder import (
            build_pipeline_runner as _build_pipeline_runner_impl,
        )

        return _build_pipeline_runner_impl(*args, **kwargs)


__all__ = [
    "build_pipeline_runner",
]
