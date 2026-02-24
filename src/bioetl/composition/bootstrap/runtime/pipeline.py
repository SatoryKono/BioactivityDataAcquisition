"""Bootstrap function for main pipeline execution.

Contains the primary Composition Root entry point for creating
a fully configured PipelineRunner ready for execution.

This is the main entry point for runtime pipeline execution.
CLI commands should use this via composition/entrypoints.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime.assembly import assemble_filter_config
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_observability_bundle,
)
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.providers.registration import register_all_providers
from bioetl.composition.registry import PipelineRegistry, get_default_registry
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner
from bioetl.infrastructure.config import get_settings, load_pipeline_config

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import PipelineRunContext

__all__ = [
    "bootstrap_pipeline_runner",
]


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.

    This is the main entry point for creating a pipeline runner. It:
    1. Registers all providers and pipelines (idempotent)
    2. Loads settings and YAML configuration
    3. Bootstraps observability (logging, tracing, metrics)
    4. Builds filter configuration from CLI/YAML
    5. Delegates to the appropriate factory to create the runner

    Layer: Returns application-level runner (PipelineRunner) ready for execution.

    Args:
        ctx: Pipeline run context containing launch parameters including
            pipeline_name, run_id, run_type, resume flag, limit, filters, etc.
        registry: Optional PipelineRegistry instance. If None, uses the
            default global registry. Pass a custom registry for test isolation.

    Returns:
        PipelineRunner: Fully configured runner ready for execution.

    Example:
        >>> from bioetl.domain.context import PipelineRunContext
        >>> from bioetl.domain.types import RunType
        >>> from uuid import uuid4
        >>>
        >>> ctx = PipelineRunContext(
        ...     pipeline_name="chembl_activity",
        ...     run_id=uuid4(),
        ...     run_type=RunType.INCREMENTAL,
        ... )
        >>> runner = bootstrap_pipeline_runner(ctx)
        >>> await runner.run()

        # For test isolation:
        >>> from bioetl.composition.registry import create_registry
        >>> registry = create_registry()
        >>> register_all_pipelines(registry=registry)
        >>> runner = bootstrap_pipeline_runner(ctx, registry=registry)
    """
    # Explicit registration retained for deterministic bootstrap semantics.
    register_all_providers()
    register_all_pipelines(registry=registry)

    return build_pipeline_runner(
        ctx=ctx,
        registry=registry,
        get_default_registry_fn=get_default_registry,
        register_all_providers_fn=register_all_providers,
        register_all_pipelines_fn=register_all_pipelines,
        get_settings_fn=get_settings,
        load_pipeline_config_fn=load_pipeline_config,
        build_observability_bundle_fn=bootstrap_observability_bundle,
        assemble_filter_config_fn=assemble_filter_config,
    )
