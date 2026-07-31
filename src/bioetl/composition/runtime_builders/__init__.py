"""Leaf runtime builders used by composition factories and bootstrap wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.lazy_exports import install_lazy_exports
from bioetl.composition.runtime_builders.registry_manifest import PUBLIC_LAZY_EXPORTS

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.composition.runtime_builders.ledger_collaborator import (
        PipelineRunnerProtocol,
    )
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerBuilderWiring,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings

    def build_pipeline_runner(
        ctx: PipelineRunContext,
        registry: PipelineRegistry | None = None,
        *,
        wiring: RunnerBuilderWiring | None = ...,
    ) -> PipelineRunnerProtocol: ...

    def control_plane_root(
        settings: Settings,
        store_name: str,
    ) -> Path: ...


__all__ = [
    "build_pipeline_runner",
    "control_plane_root",
]
install_lazy_exports(
    module_globals=globals(),
    public_exports=PUBLIC_LAZY_EXPORTS,
    module_name=__name__,
    explicit_exports=__all__,
)
