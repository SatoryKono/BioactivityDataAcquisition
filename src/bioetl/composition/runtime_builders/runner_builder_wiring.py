"""Typed dependency bundles for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders.inputs_runtime_assembly import (
    ResolvedVacuumSettings,
    assemble_cached_bronze_context,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
)
from bioetl.composition.runtime_builders.config_access import (
    load_source_config as load_runtime_builder_source_config,
)
from bioetl.domain.config import RuntimeConfig
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.infrastructure.config.settings_api import get_settings

if TYPE_CHECKING:
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class RunnerFactoryWiring:
    """Provider and registry wiring needed before runner construction."""

    create_registry: Callable[[], PipelineRegistry] = create_registry
    ensure_providers_loaded: Callable[[], None] = ensure_providers_loaded
    register_all_pipelines: Callable[..., None] = register_all_pipelines


@dataclass(frozen=True, slots=True)
class RunnerInputWiring:
    """Config, observability, and runtime-input wiring for runner construction."""

    get_settings: Callable[[], Settings] = get_settings
    load_pipeline_config: Callable[[str], PipelineYamlConfig] = load_pipeline_config
    load_source_config: Callable[..., object] = load_runtime_builder_source_config
    build_observability_bundle: Callable[..., ObservabilityBundle] | None = None
    assemble_vacuum_settings: Callable[..., ResolvedVacuumSettings] = (
        assemble_vacuum_settings
    )
    assemble_runtime_config: Callable[..., RuntimeConfig] = assemble_runtime_config
    assemble_filter_config: Callable[..., InputFilterConfig | None] = (
        assemble_filter_config
    )
    assemble_cached_bronze_context: Callable[
        [PipelineRunContext], CachedBronzeContext
    ] = assemble_cached_bronze_context


@dataclass(frozen=True, slots=True)
class RunnerBuilderWiring:
    """Canonical aggregate wiring seam for runtime runner construction."""

    factory: RunnerFactoryWiring = field(default_factory=RunnerFactoryWiring)
    inputs: RunnerInputWiring = field(default_factory=RunnerInputWiring)


@dataclass(frozen=True, slots=True)
class LegacyRunnerBuilderOverrides:
    """Legacy keyword overrides retained for focused tests and migration."""

    create_registry_fn: Callable[[], PipelineRegistry] | None = None
    ensure_providers_loaded_fn: Callable[[], None] | None = None
    register_all_pipelines_fn: Callable[..., None] | None = None
    get_settings_fn: Callable[[], Settings] | None = None
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None = None
    load_source_config_fn: Callable[..., object] | None = None
    build_observability_bundle_fn: Callable[..., ObservabilityBundle] | None = None
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings] | None = None
    assemble_runtime_config_fn: Callable[..., RuntimeConfig] | None = None
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None] | None = None
    assemble_cached_bronze_context_fn: (
        Callable[[PipelineRunContext], CachedBronzeContext] | None
    ) = None


def resolve_runner_factory_wiring(
    wiring: RunnerFactoryWiring | None = None,
    *,
    create_registry_fn: Callable[[], PipelineRegistry] | None = None,
    ensure_providers_loaded_fn: Callable[[], None] | None = None,
    register_all_pipelines_fn: Callable[..., None] | None = None,
) -> RunnerFactoryWiring:
    """Return factory wiring with legacy keyword overrides applied."""
    resolved = wiring or RunnerFactoryWiring()
    if (
        create_registry_fn is None
        and ensure_providers_loaded_fn is None
        and register_all_pipelines_fn is None
    ):
        return resolved
    return RunnerFactoryWiring(
        create_registry=(
            create_registry_fn
            if create_registry_fn is not None
            else resolved.create_registry
        ),
        ensure_providers_loaded=(
            ensure_providers_loaded_fn
            if ensure_providers_loaded_fn is not None
            else resolved.ensure_providers_loaded
        ),
        register_all_pipelines=(
            register_all_pipelines_fn
            if register_all_pipelines_fn is not None
            else resolved.register_all_pipelines
        ),
    )


def resolve_runner_builder_wiring(
    wiring: RunnerBuilderWiring | None = None,
    *,
    factory_wiring: RunnerFactoryWiring | None = None,
    input_wiring: RunnerInputWiring | None = None,
    legacy_overrides: LegacyRunnerBuilderOverrides | None = None,
) -> RunnerBuilderWiring:
    """Return aggregate runner wiring with legacy keyword overrides applied."""
    resolved = wiring or RunnerBuilderWiring()
    overrides = legacy_overrides or LegacyRunnerBuilderOverrides()
    resolved_factory = resolve_runner_factory_wiring(
        factory_wiring or resolved.factory,
        create_registry_fn=overrides.create_registry_fn,
        ensure_providers_loaded_fn=overrides.ensure_providers_loaded_fn,
        register_all_pipelines_fn=overrides.register_all_pipelines_fn,
    )
    resolved_inputs = resolve_runner_input_wiring(
        input_wiring or resolved.inputs,
        get_settings_fn=overrides.get_settings_fn,
        load_pipeline_config_fn=overrides.load_pipeline_config_fn,
        load_source_config_fn=overrides.load_source_config_fn,
        build_observability_bundle_fn=overrides.build_observability_bundle_fn,
        assemble_vacuum_settings_fn=overrides.assemble_vacuum_settings_fn,
        assemble_runtime_config_fn=overrides.assemble_runtime_config_fn,
        assemble_filter_config_fn=overrides.assemble_filter_config_fn,
        assemble_cached_bronze_context_fn=overrides.assemble_cached_bronze_context_fn,
    )
    if resolved_factory is resolved.factory and resolved_inputs is resolved.inputs:
        return resolved
    return RunnerBuilderWiring(factory=resolved_factory, inputs=resolved_inputs)


def resolve_runner_input_wiring(
    wiring: RunnerInputWiring | None = None,
    *,
    get_settings_fn: Callable[[], Settings] | None = None,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None = None,
    load_source_config_fn: Callable[..., object] | None = None,
    build_observability_bundle_fn: Callable[..., ObservabilityBundle] | None = None,
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings] | None = None,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig] | None = None,
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None] | None = None,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ]
    | None = None,
) -> RunnerInputWiring:
    """Return input wiring with legacy keyword overrides applied."""
    resolved = wiring or RunnerInputWiring()
    if (
        get_settings_fn is None
        and load_pipeline_config_fn is None
        and load_source_config_fn is None
        and build_observability_bundle_fn is None
        and assemble_vacuum_settings_fn is None
        and assemble_runtime_config_fn is None
        and assemble_filter_config_fn is None
        and assemble_cached_bronze_context_fn is None
    ):
        return resolved
    return RunnerInputWiring(
        get_settings=(
            get_settings_fn if get_settings_fn is not None else resolved.get_settings
        ),
        load_pipeline_config=(
            load_pipeline_config_fn
            if load_pipeline_config_fn is not None
            else resolved.load_pipeline_config
        ),
        load_source_config=(
            load_source_config_fn
            if load_source_config_fn is not None
            else resolved.load_source_config
        ),
        build_observability_bundle=(
            build_observability_bundle_fn
            if build_observability_bundle_fn is not None
            else resolved.build_observability_bundle
        ),
        assemble_vacuum_settings=(
            assemble_vacuum_settings_fn
            if assemble_vacuum_settings_fn is not None
            else resolved.assemble_vacuum_settings
        ),
        assemble_runtime_config=(
            assemble_runtime_config_fn
            if assemble_runtime_config_fn is not None
            else resolved.assemble_runtime_config
        ),
        assemble_filter_config=(
            assemble_filter_config_fn
            if assemble_filter_config_fn is not None
            else resolved.assemble_filter_config
        ),
        assemble_cached_bronze_context=(
            assemble_cached_bronze_context_fn
            if assemble_cached_bronze_context_fn is not None
            else resolved.assemble_cached_bronze_context
        ),
    )


__all__ = [
    "LegacyRunnerBuilderOverrides",
    "RunnerBuilderWiring",
    "RunnerFactoryWiring",
    "RunnerInputWiring",
    "resolve_runner_builder_wiring",
    "resolve_runner_factory_wiring",
    "resolve_runner_input_wiring",
]
