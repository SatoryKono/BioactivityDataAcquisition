"""Main composition-root bootstrap for runtime pipeline execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap.runtime.assembly import assemble_filter_config
from bioetl.composition.bootstrap.runtime.compatibility import (
    apply_runtime_compatibility_patches,
)
from bioetl.composition.bootstrap.runtime.observability import bootstrap_observability_bundle
from bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases import initialize_runtime_policy_sources
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders.config_access import (
    create_pipeline_config_loader,
    create_source_config_loader,
    get_settings,
)
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner
from bioetl.composition.runtime_builders.runner_builder_wiring import RunnerFactoryWiring, RunnerInputWiring
from bioetl.infrastructure.config.config_root import resolve_configs_root

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = ["bootstrap_pipeline_runner"]


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None = None,
) -> PipelineRunner:
    """Build one ready-to-run pipeline runner from runtime context and registry."""
    apply_runtime_compatibility_patches()
    effective_registry = registry or create_registry()
    ensure_providers_loaded()
    if not effective_registry.list_pipelines():
        register_all_pipelines(registry=effective_registry)
    effective_registry.get(ctx.pipeline_name)
    configs_root = resolve_configs_root()
    initialize_runtime_policy_sources(configs_root)
    pipeline_config_loader = load_pipeline_config_fn or create_pipeline_config_loader(configs_root)
    return cast(
        "PipelineRunner",
        build_pipeline_runner(
            ctx=ctx,
            registry=effective_registry,
            factory_wiring=RunnerFactoryWiring(
                ensure_providers_loaded=lambda: None,
                register_all_pipelines=lambda registry=None: None,
            ),
            input_wiring=RunnerInputWiring(
                get_settings=get_settings,
                load_pipeline_config=pipeline_config_loader,
                load_source_config=create_source_config_loader(configs_root),
                build_observability_bundle=bootstrap_observability_bundle,
                assemble_filter_config=assemble_filter_config,
            ),
        ),
    )
