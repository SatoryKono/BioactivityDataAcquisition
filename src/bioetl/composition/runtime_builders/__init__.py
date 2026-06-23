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

    def control_plane_root(
        settings: object,
        store_name: str,
    ) -> object: ...

else:

    def build_pipeline_runner(*args: object, **kwargs: object) -> object:
        """Lazily dispatch to the concrete runner builder without package import cycles."""
        from bioetl.composition.runtime_builders.runner_builder import (
            build_pipeline_runner as _build_pipeline_runner_impl,
        )

        return _build_pipeline_runner_impl(*args, **kwargs)

    def control_plane_root(*args: object, **kwargs: object) -> object:
        """Lazily dispatch to the concrete control-plane root builder without package import cycles."""
        from bioetl.composition.runtime_builders._run_manifest_data_roots import (
            control_plane_root as _control_plane_root_impl,
        )

        return _control_plane_root_impl(*args, **kwargs)


__all__ = [
    "build_pipeline_runner",
    "control_plane_root",
]
