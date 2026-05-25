"""Phase helpers for runtime pipeline bootstrap assembly."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime.assembly import assemble_filter_config
from bioetl.composition.bootstrap.runtime.classification_init import (
    initialize_publication_type_classification,
)
from bioetl.composition.bootstrap.runtime.normalization_policy_init import (
    initialize_chembl_policy_registry,
)
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_observability_bundle,
)
from bioetl.composition.bootstrap.runtime.publication_vocab_init import (
    initialize_publication_controlled_vocabulary,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders.config_access import (
    create_pipeline_config_loader,
    create_source_config_loader,
    get_settings,
)
from bioetl.composition.runtime_builders.runner_builder_wiring import (
    RunnerFactoryWiring,
    RunnerInputWiring,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "build_bootstrap_runner_factory_wiring",
    "build_bootstrap_runner_input_wiring",
    "initialize_runtime_policy_sources",
    "prepare_runtime_registry",
]


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


def build_bootstrap_runner_factory_wiring() -> RunnerFactoryWiring:
    """Return no-op factory wiring after bootstrap has already populated registry."""
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
