"""Main composition-root bootstrap for runtime pipeline execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap.runtime.assembly import RuntimeBootstrapPhases
from bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases import (
    build_runtime_bootstrap_phases_with_registry, prepare_runtime_registry,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.runtime_builders.config_access import resolve_configs_root
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner as _build_pipeline_runner
from bioetl.infrastructure.compat.pandera_compat import apply_pandera_typing_compat_if_needed

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "RuntimeBootstrapPhases", "apply_runtime_compatibility_patches",
    "bootstrap_pipeline_runner", "build_runtime_bootstrap_phases",
]


def apply_runtime_compatibility_patches() -> bool:
    """Apply the idempotent third-party Pandera runtime patch."""
    return apply_pandera_typing_compat_if_needed()


def build_runtime_bootstrap_phases(
    *,
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None,
) -> RuntimeBootstrapPhases:
    """Resolve explicit runtime bootstrap phases before runner construction."""
    apply_runtime_compatibility_patches()
    effective_registry = prepare_runtime_registry(
        registry=registry,
        pipeline_name=ctx.pipeline_name,
    )
    return build_runtime_bootstrap_phases_with_registry(
        registry=effective_registry,
        load_pipeline_config_fn=load_pipeline_config_fn,
        resolve_configs_root_fn=resolve_configs_root,
    )


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None = None,
) -> PipelineRunner:
    """Build one ready-to-run pipeline runner from runtime context and registry."""
    apply_runtime_compatibility_patches()
    effective_registry = prepare_runtime_registry(
        registry=registry,
        pipeline_name=ctx.pipeline_name,
    )
    phases = build_runtime_bootstrap_phases_with_registry(
        registry=effective_registry,
        load_pipeline_config_fn=load_pipeline_config_fn,
        resolve_configs_root_fn=resolve_configs_root,
    )
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerBuilderWiring,
    )

    wiring = RunnerBuilderWiring(
        factory=phases.factory_wiring,
        inputs=phases.input_wiring,
    )
    return cast(
        "PipelineRunner",
        _build_pipeline_runner(ctx=ctx, registry=phases.registry, wiring=wiring),
    )
