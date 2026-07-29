"""Phase helpers for runtime pipeline bootstrap assembly."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime._pipeline_bootstrap_lazy_dependencies import (
    initialize_chembl_policy_registry,
    initialize_protein_class_target_type_mapping,
    initialize_publication_controlled_vocabulary,
    initialize_publication_type_classification,
    register_all_pipelines,
)

if TYPE_CHECKING:
    from uuid import UUID

    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.composition.bootstrap.runtime.assembly import RuntimeBootstrapPhases
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerFactoryWiring,
        RunnerInputWiring,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        AuditPort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterYamlConfig,
        PipelineYamlConfig,
    )

__all__ = [
    "build_bootstrap_runner_factory_wiring",
    "build_bootstrap_runner_input_wiring",
    "build_runtime_bootstrap_phases_with_registry",
    "initialize_runtime_policy_sources",
    "prepare_runtime_registry",
]


def _noop_ensure_providers_loaded() -> None:
    """No-op implementation for bootstrap phase."""
    pass


def _noop_register_all_pipelines(registry: object = None) -> None:
    """No-op implementation for bootstrap phase."""
    pass


def assemble_filter_config(
    *,
    yaml_filter: InputFilterYamlConfig,
    ctx: PipelineRunContext,
    test_mode: bool,
) -> InputFilterConfig | None:
    """Lazy wrapper for the bootstrap filter-config assembler seam."""
    from bioetl.composition.bootstrap.runtime.assembly import (
        assemble_filter_config as _assemble_filter_config,
    )

    return _assemble_filter_config(
        yaml_filter=yaml_filter,
        ctx=ctx,
        test_mode=test_mode,
    )


def bootstrap_observability_bundle(
    *,
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str,
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort] | None = None,
    tracer_bootstrapper: Callable[[Settings], TracingPort] | None = None,
    metrics_bootstrapper: Callable[[Settings], MetricsPort] | None = None,
    audit_bootstrapper: Callable[
        [Settings, LoggerPort, MetricsPort, TracingPort], AuditPort
    ]
    | None = None,
    dq_monitor_bootstrapper: Callable[
        [Settings, LoggerPort | None], DQMonitorPort | None
    ]
    | None = None,
    preflight_validator: Callable[..., None] | None = None,
    yaml_config: object | None = None,
    skip_gold: bool = False,
) -> ObservabilityBundle:
    """Lazy wrapper for bootstrap observability wiring."""
    from bioetl.composition.bootstrap.runtime.observability_bundle import (
        bootstrap_observability_bundle_impl as _bootstrap_observability_bundle,
    )

    bootstrap: Callable[..., ObservabilityBundle] = _bootstrap_observability_bundle
    bootstrap_kwargs: dict[str, object] = {
        "pipeline": pipeline,
        "run_id": run_id,
        "settings": settings,
        "log_level": log_level,
        "logger_bootstrapper": logger_bootstrapper,
        "tracer_bootstrapper": tracer_bootstrapper,
        "metrics_bootstrapper": metrics_bootstrapper,
        "audit_bootstrapper": audit_bootstrapper,
        "dq_monitor_bootstrapper": dq_monitor_bootstrapper,
        "preflight_validator": preflight_validator,
        "yaml_config": yaml_config,
        "skip_gold": skip_gold,
    }
    return bootstrap(**bootstrap_kwargs)


def create_pipeline_config_loader(
    configs_root: Path,
) -> Callable[[str], PipelineYamlConfig]:
    """Lazy wrapper for pipeline-config loader construction."""
    from bioetl.composition.runtime_builders.config_access import (
        create_pipeline_config_loader as _create_pipeline_config_loader,
    )

    return _create_pipeline_config_loader(configs_root)


def create_registry() -> PipelineRegistry:
    """Lazy wrapper for registry construction."""
    from bioetl.composition.registry_api import create_registry as _create_registry

    return _create_registry()


def create_source_config_loader(configs_root: Path) -> Callable[[str], object]:
    """Lazy wrapper for source-config loader construction."""
    from bioetl.composition.runtime_builders.config_access import (
        create_source_config_loader as _create_source_config_loader,
    )

    return _create_source_config_loader(configs_root)


def ensure_providers_loaded() -> None:
    """Lazy wrapper for provider registration discovery."""
    from bioetl.composition.providers import (
        ensure_providers_loaded as _ensure_providers_loaded,
    )

    _ensure_providers_loaded()


def get_settings() -> Settings:
    """Lazy wrapper for runtime settings access."""
    from bioetl.composition.runtime_builders.config_access import (
        get_settings as _get_settings,
    )

    return _get_settings()


def prepare_runtime_registry(
    *,
    registry: PipelineRegistry | None,
    pipeline_name: str,
) -> PipelineRegistry:
    """Resolve and populate the runtime pipeline registry phase."""
    effective_registry = registry if registry is not None else create_registry()
    ensure_providers_loaded()
    if not effective_registry.list_pipelines():
        register_all_pipelines(registry=effective_registry)
    effective_registry.get(pipeline_name)
    return effective_registry


def initialize_runtime_policy_sources(configs_root: Path) -> None:
    """Initialize runtime policy/vocabulary registries from the config root."""
    initialize_chembl_policy_registry(configs_root)
    initialize_publication_type_classification(configs_root)
    initialize_protein_class_target_type_mapping(configs_root)
    initialize_publication_controlled_vocabulary(configs_root)


def build_runtime_bootstrap_phases_with_registry(
    *,
    registry: PipelineRegistry,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None,
    resolve_configs_root_fn: Callable[[], Path],
) -> RuntimeBootstrapPhases:
    """Assemble runtime phases after the registry phase has completed."""
    from bioetl.composition.bootstrap.runtime.assembly import (
        assemble_runtime_bootstrap_phases,
    )

    configs_root = resolve_configs_root_fn()
    initialize_runtime_policy_sources(configs_root)
    return assemble_runtime_bootstrap_phases(
        registry=registry,
        configs_root=configs_root,
        factory_wiring=build_bootstrap_runner_factory_wiring(),
        input_wiring=build_bootstrap_runner_input_wiring(
            configs_root=configs_root,
            load_pipeline_config_fn=load_pipeline_config_fn,
        ),
    )


def build_bootstrap_runner_factory_wiring() -> RunnerFactoryWiring:
    """Return no-op factory wiring after bootstrap has already populated registry."""
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerFactoryWiring,
    )

    return RunnerFactoryWiring(
        ensure_providers_loaded=_noop_ensure_providers_loaded,
        register_all_pipelines=_noop_register_all_pipelines,
    )


def build_bootstrap_runner_input_wiring(
    *,
    configs_root: Path,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None,
) -> RunnerInputWiring:
    """Build the typed input wiring bundle for runtime runner construction."""
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerInputWiring,
    )

    pipeline_config_loader = (
        load_pipeline_config_fn
        if load_pipeline_config_fn is not None
        else create_pipeline_config_loader(configs_root)
    )
    return RunnerInputWiring(
        get_settings=get_settings,
        load_pipeline_config=pipeline_config_loader,
        load_source_config=create_source_config_loader(configs_root),
        build_observability_bundle=bootstrap_observability_bundle,
        assemble_filter_config=assemble_filter_config,
    )
