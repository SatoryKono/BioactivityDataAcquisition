"""Phase helpers for runtime pipeline bootstrap assembly."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.bootstrap.runtime.assembly import RuntimeBootstrapPhases
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerFactoryWiring,
        RunnerInputWiring,
    )
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "build_bootstrap_runner_factory_wiring",
    "build_bootstrap_runner_input_wiring",
    "build_runtime_bootstrap_phases_with_registry",
    "initialize_runtime_policy_sources",
    "prepare_runtime_registry",
]


def assemble_filter_config(*args: object, **kwargs: object) -> object:
    """Lazy wrapper for the bootstrap filter-config assembler seam."""
    from bioetl.composition.bootstrap.runtime.assembly import (
        assemble_filter_config as _assemble_filter_config,
    )

    return _assemble_filter_config(*args, **kwargs)


def bootstrap_observability_bundle(*args: object, **kwargs: object) -> object:
    """Lazy wrapper for bootstrap observability wiring."""
    from bioetl.composition.bootstrap.runtime.observability import (
        bootstrap_observability_bundle as _bootstrap_observability_bundle,
    )

    return _bootstrap_observability_bundle(*args, **kwargs)


def create_pipeline_config_loader(configs_root: Path) -> Callable[[str], object]:
    """Lazy wrapper for pipeline-config loader construction."""
    from bioetl.composition.runtime_builders.config_access import (
        create_pipeline_config_loader as _create_pipeline_config_loader,
    )

    return _create_pipeline_config_loader(configs_root)


def create_registry() -> PipelineRegistry:
    """Lazy wrapper for registry construction."""
    from bioetl.composition.registry_api import create_registry as _create_registry

    return _create_registry()


def create_source_config_loader(configs_root: Path) -> Callable[..., object]:
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


def get_settings() -> object:
    """Lazy wrapper for runtime settings access."""
    from bioetl.composition.runtime_builders.config_access import (
        get_settings as _get_settings,
    )

    return _get_settings()


def initialize_chembl_policy_registry(configs_root: Path) -> None:
    """Lazy wrapper for ChEMBL normalization policy initialization."""
    from bioetl.composition.bootstrap.runtime.normalization_policy_init import (
        initialize_chembl_policy_registry as _initialize_chembl_policy_registry,
    )

    _initialize_chembl_policy_registry(configs_root)


def initialize_publication_controlled_vocabulary(configs_root: Path) -> None:
    """Lazy wrapper for publication controlled vocabulary initialization."""
    from bioetl.composition.bootstrap.runtime.publication_vocab_init import (
        initialize_publication_controlled_vocabulary as _initialize_publication_controlled_vocabulary,
    )

    _initialize_publication_controlled_vocabulary(configs_root)


def initialize_publication_type_classification(configs_root: Path) -> None:
    """Lazy wrapper for publication type classification initialization."""
    from bioetl.composition.bootstrap.runtime.classification_init import (
        initialize_publication_type_classification as _initialize_publication_type_classification,
    )

    _initialize_publication_type_classification(configs_root)


def register_all_pipelines(*args: object, **kwargs: object) -> object:
    """Lazy wrapper for full pipeline registration."""
    from bioetl.composition.factories.pipeline.registry import (
        register_all_pipelines as _register_all_pipelines,
    )

    return _register_all_pipelines(*args, **kwargs)


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
        ensure_providers_loaded=lambda: None,
        register_all_pipelines=lambda registry=None: None,
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
