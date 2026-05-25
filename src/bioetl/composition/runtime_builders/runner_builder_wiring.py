"""Typed dependency bundles for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
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
)
from bioetl.domain.config import RuntimeConfig

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
    load_source_config: Callable[..., object] = load_source_config
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


def resolve_runner_factory_wiring(
    wiring: RunnerFactoryWiring | None = None,
    *,
    create_registry_fn: Callable[[], PipelineRegistry] | None = None,
    ensure_providers_loaded_fn: Callable[[], None] | None = None,
    register_all_pipelines_fn: Callable[..., None] | None = None,
) -> RunnerFactoryWiring:
    """Return factory wiring with legacy keyword overrides applied."""
    resolved = wiring or RunnerFactoryWiring()
    overrides: dict[str, object] = {}
    if create_registry_fn is not None:
        overrides["create_registry"] = create_registry_fn
    if ensure_providers_loaded_fn is not None:
        overrides["ensure_providers_loaded"] = ensure_providers_loaded_fn
    if register_all_pipelines_fn is not None:
        overrides["register_all_pipelines"] = register_all_pipelines_fn
    return replace(resolved, **overrides) if overrides else resolved


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
    overrides: dict[str, object] = {}
    if get_settings_fn is not None:
        overrides["get_settings"] = get_settings_fn
    if load_pipeline_config_fn is not None:
        overrides["load_pipeline_config"] = load_pipeline_config_fn
    if load_source_config_fn is not None:
        overrides["load_source_config"] = load_source_config_fn
    if build_observability_bundle_fn is not None:
        overrides["build_observability_bundle"] = build_observability_bundle_fn
    if assemble_vacuum_settings_fn is not None:
        overrides["assemble_vacuum_settings"] = assemble_vacuum_settings_fn
    if assemble_runtime_config_fn is not None:
        overrides["assemble_runtime_config"] = assemble_runtime_config_fn
    if assemble_filter_config_fn is not None:
        overrides["assemble_filter_config"] = assemble_filter_config_fn
    if assemble_cached_bronze_context_fn is not None:
        overrides["assemble_cached_bronze_context"] = assemble_cached_bronze_context_fn
    return replace(resolved, **overrides) if overrides else resolved


__all__ = [
    "RunnerFactoryWiring",
    "RunnerInputWiring",
    "resolve_runner_factory_wiring",
    "resolve_runner_input_wiring",
]
