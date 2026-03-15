"""Bootstrap function for main pipeline execution.

Contains the primary Composition Root entry point for creating
a fully configured PipelineRunner ready for execution.

This is the main entry point for runtime pipeline execution.
CLI commands should use this via composition/entrypoints.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime.assembly import assemble_filter_config
from bioetl.composition.bootstrap.runtime.classification_init import (
    initialize_publication_type_classification,
)
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_observability_bundle,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.composition.registry import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner
from bioetl.infrastructure.config import get_settings, load_pipeline_config

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import PipelineRunContext

__all__ = [
    # Deprecated alias (backward compatibility)
    "bootstrap_pipeline",
    # Canonical name (use this)
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
    # Classification data must be available before transformers run.
    initialize_publication_type_classification(Path("configs"))
    effective_registry = registry if registry is not None else create_registry()

    # Keep runtime bootstrap behind the registry facade while preserving
    # deterministic explicit registration in this composition root.
    ProviderRegistry.ensure_loaded()
    if not effective_registry.list_pipelines():
        register_all_pipelines(registry=effective_registry)

    return build_pipeline_runner(
        ctx=ctx,
        registry=effective_registry,
        ensure_providers_loaded_fn=lambda: None,
        register_all_pipelines_fn=lambda registry=None: None,
        get_settings_fn=get_settings,
        load_pipeline_config_fn=load_pipeline_config,
        build_observability_bundle_fn=bootstrap_observability_bundle,
        assemble_filter_config_fn=assemble_filter_config,
    )


def bootstrap_pipeline(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.


    Args:
        ctx: Pipeline run context containing launch parameters.
        registry: Optional PipelineRegistry instance.

    Returns:
        PipelineRunner: Fully configured runner ready for execution.
    """
    return bootstrap_pipeline_runner(ctx=ctx, registry=registry)
