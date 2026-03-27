"""Leaf builder for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.composition import PipelineRegistry, create_registry
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.runtime_builders.config_access import (
    get_settings,
    load_pipeline_config,
    load_source_config,
)
from bioetl.composition.runtime_builders.inputs_resolver import (
    ResolvedVacuumSettings,
    assemble_cached_bronze_context,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
    prepare_runner_inputs,
)
from bioetl.composition.runtime_builders.inputs_resolver import (
    RunnerInputs as _RunnerInputs,
)
from bioetl.composition.runtime_builders.observability_builder import (
    build_observability_bundle,
)
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import PipelineFactoryPort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        PipelineYamlConfig,
    )


__all__ = ["build_pipeline_runner"]


def _initialize_registry(
    *,
    registry: PipelineRegistry | None,
    create_registry_fn: Callable[[], PipelineRegistry],
    ensure_providers_loaded_fn: Callable[[], None],
    register_all_pipelines_fn: Callable[..., None],
) -> PipelineRegistry:
    """Initialize provider/pipeline registry with optional explicit registry."""
    effective_registry = registry if registry is not None else create_registry_fn()
    ensure_providers_loaded_fn()
    register_all_pipelines_fn(registry=effective_registry)
    return effective_registry


def _create_runner_from_factory(
    *,
    factory: PipelineFactoryPort,
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> PipelineRunner:
    return cast(
        "PipelineRunner",
        factory.create_runner(
            run_id=ctx.run_id,
            runtime=inputs.runtime_config,
            settings=inputs.settings,  # type: ignore
            observability=inputs.observability,  # type: ignore
            filter_config=inputs.filter_config,
            config=inputs.yaml_config,
            cached_bronze=inputs.cached_bronze,
        ),
    )


def build_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    create_registry_fn: Callable[[], PipelineRegistry] = create_registry,
    ensure_providers_loaded_fn: Callable[[], None] = ensure_providers_loaded,
    register_all_pipelines_fn: Callable[..., None] = register_all_pipelines,
    get_settings_fn: Callable[[], Settings] = get_settings,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] = load_pipeline_config,
    load_source_config_fn: Callable[..., object] = load_source_config,
    build_observability_bundle_fn: Callable[..., ObservabilityBundle] | None = None,
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings] | None = None,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig] | None = None,
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None] | None = None,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ]
    | None = None,
) -> PipelineRunner:
    """Assemble and return a fully configured ``PipelineRunner``.

    Args:
        ctx: Pipeline run context containing pipeline name, run type, and execution options.
        registry: Optional PipelineRegistry for test isolation; creates a fresh
            runtime registry when None.
        create_registry_fn: Callable returning a fresh PipelineRegistry instance.
        ensure_providers_loaded_fn: Callable ensuring provider adapters are loaded.
        register_all_pipelines_fn: Callable registering all pipeline factories.
        get_settings_fn: Callable returning global application Settings.
        load_pipeline_config_fn: Callable loading PipelineYamlConfig by pipeline name.
        build_observability_bundle_fn: Optional callable returning an ObservabilityBundle.
            Uses the canonical observability builder when omitted.
        assemble_vacuum_settings_fn: Optional callable merging CLI and YAML vacuum
            settings. Uses the canonical runtime input resolver when omitted.
        assemble_runtime_config_fn: Optional callable building RuntimeConfig from
            context. Uses the canonical runtime input resolver when omitted.
        assemble_filter_config_fn: Optional callable building InputFilterConfig from
            YAML and CLI. Uses the canonical runtime input resolver when omitted.
        assemble_cached_bronze_context_fn: Optional callable resolving cached bronze
            context. Uses the canonical runtime input resolver when omitted.

    Returns:
        Fully configured PipelineRunner ready for execution.
    """
    effective_registry = _initialize_registry(
        registry=registry,
        create_registry_fn=create_registry_fn,
        ensure_providers_loaded_fn=ensure_providers_loaded_fn,
        register_all_pipelines_fn=register_all_pipelines_fn,
    )
    build_observability_bundle_impl = (
        build_observability_bundle
        if build_observability_bundle_fn is None
        else build_observability_bundle_fn
    )
    assemble_vacuum_settings_impl = (
        assemble_vacuum_settings
        if assemble_vacuum_settings_fn is None
        else assemble_vacuum_settings_fn
    )
    assemble_runtime_config_impl = (
        assemble_runtime_config
        if assemble_runtime_config_fn is None
        else assemble_runtime_config_fn
    )
    assemble_filter_config_impl = (
        assemble_filter_config
        if assemble_filter_config_fn is None
        else assemble_filter_config_fn
    )
    assemble_cached_bronze_context_impl = (
        assemble_cached_bronze_context
        if assemble_cached_bronze_context_fn is None
        else assemble_cached_bronze_context_fn
    )
    inputs = prepare_runner_inputs(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=build_observability_bundle_impl,
        assemble_vacuum_settings_fn=assemble_vacuum_settings_impl,
        assemble_runtime_config_fn=assemble_runtime_config_impl,
        assemble_filter_config_fn=assemble_filter_config_impl,
        assemble_cached_bronze_context_fn=assemble_cached_bronze_context_impl,
        load_source_config_fn=load_source_config_fn,
    )
    return _create_runner_from_factory(
        factory=effective_registry.get(ctx.pipeline_name).factory,
        ctx=ctx,
        inputs=inputs,
    )
