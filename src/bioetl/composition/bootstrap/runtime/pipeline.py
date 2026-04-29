"""Main composition-root bootstrap for runtime pipeline execution."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

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
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders.config_access import (
    get_settings,
    load_pipeline_config,
)
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.context import PipelineRunContext

__all__ = [
    "bootstrap_pipeline_runner",
]


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Build a ready-to-run pipeline runner from runtime context and registry.

    Initializes publication type classification data, registers all providers
    and pipelines, then delegates to the runtime builder to wire all
    infrastructure dependencies.

    Args:
        ctx: Pipeline run context containing launch parameters such as pipeline
            name, run type, limit, filter settings, and observability options.
        registry: Optional PipelineRegistry to use instead of a fresh runtime
            registry; useful for test isolation.

    Returns:
        Fully configured PipelineRunner ready for execution.
    """
    # Normalization policy data must be available before profiles/transformers run.
    initialize_chembl_policy_registry(Path("configs"))
    initialize_publication_type_classification(Path("configs"))
    effective_registry = registry if registry is not None else create_registry()

    # Keep runtime bootstrap behind the registry facade with deterministic registration.
    ensure_providers_loaded()
    if not effective_registry.list_pipelines():
        register_all_pipelines(registry=effective_registry)

    return cast(
        "PipelineRunner",
        build_pipeline_runner(
            ctx=ctx,
            registry=effective_registry,
            ensure_providers_loaded_fn=lambda: None,
            register_all_pipelines_fn=lambda registry=None: None,
            get_settings_fn=get_settings,
            load_pipeline_config_fn=load_pipeline_config,
            build_observability_bundle_fn=bootstrap_observability_bundle,
            assemble_filter_config_fn=assemble_filter_config,
        ),
    )
