"""Main composition-root bootstrap for runtime pipeline execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap.runtime.compatibility import (
    apply_runtime_compatibility_patches,
)
from bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases import (
    build_bootstrap_runner_factory_wiring,
    build_bootstrap_runner_input_wiring,
    initialize_runtime_policy_sources,
    prepare_runtime_registry,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.infrastructure.config.config_root import resolve_configs_root

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.context import PipelineRunContext
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerFactoryWiring,
        RunnerInputWiring,
    )
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "RuntimeBootstrapPhases",
    "bootstrap_pipeline_runner",
    "build_runtime_bootstrap_phases",
]


@dataclass(frozen=True, slots=True)
class RuntimeBootstrapPhases:
    """Resolved runtime bootstrap phase outputs passed into runner construction."""

    registry: PipelineRegistry
    configs_root: Path
    factory_wiring: RunnerFactoryWiring
    input_wiring: RunnerInputWiring


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
    return _build_runtime_bootstrap_phases_with_registry(
        registry=effective_registry,
        load_pipeline_config_fn=load_pipeline_config_fn,
    )


def _build_runtime_bootstrap_phases_with_registry(
    *,
    registry: PipelineRegistry,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None,
) -> RuntimeBootstrapPhases:
    """Assemble runtime phases after the registry phase has completed."""
    configs_root = resolve_configs_root()
    initialize_runtime_policy_sources(configs_root)

    return RuntimeBootstrapPhases(
        registry=registry,
        configs_root=configs_root,
        factory_wiring=build_bootstrap_runner_factory_wiring(),
        input_wiring=build_bootstrap_runner_input_wiring(
            configs_root=configs_root,
            load_pipeline_config_fn=load_pipeline_config_fn,
        ),
    )


def _build_pipeline_runner(**kwargs: object) -> object:
    """Import the heavy runner builder only after runtime phases are resolved."""
    from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner

    return build_pipeline_runner(**kwargs)


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
    phases = _build_runtime_bootstrap_phases_with_registry(
        registry=effective_registry,
        load_pipeline_config_fn=load_pipeline_config_fn,
    )
    return cast(
        "PipelineRunner",
        _build_pipeline_runner(
            ctx=ctx,
            registry=phases.registry,
            factory_wiring=phases.factory_wiring,
            input_wiring=phases.input_wiring,
        ),
    )
