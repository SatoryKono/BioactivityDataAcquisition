"""Leaf runtime builders used by composition factories and bootstrap wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.composition import PipelineRegistry
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.composition.runtime_builders.inputs_resolver import (
        ResolvedVacuumSettings,
    )
    from bioetl.composition.runtime_builders.ledger_collaborator import (
        PipelineRunnerProtocol,
    )
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:

    def build_pipeline_runner(
        ctx: PipelineRunContext,
        registry: PipelineRegistry | None = None,
        *,
        create_registry_fn: Callable[[], PipelineRegistry] = ...,
        ensure_providers_loaded_fn: Callable[[], None] = ...,
        register_all_pipelines_fn: Callable[..., None] = ...,
        get_settings_fn: Callable[[], Settings] = ...,
        load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] = ...,
        load_source_config_fn: Callable[..., object] = ...,
        build_observability_bundle_fn: Callable[..., ObservabilityBundle] | None = ...,
        assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings] | None = ...,
        assemble_runtime_config_fn: Callable[..., RuntimeConfig] | None = ...,
        assemble_filter_config_fn: Callable[..., InputFilterConfig | None] | None = ...,
        assemble_cached_bronze_context_fn: Callable[
            [PipelineRunContext], CachedBronzeContext
        ]
        | None = ...,
    ) -> PipelineRunnerProtocol: ...

else:

    def build_pipeline_runner(*args: object, **kwargs: object) -> object:
        """Lazily dispatch to the concrete runner builder without package import cycles."""
        from bioetl.composition.runtime_builders.runner_builder import (
            build_pipeline_runner as _build_pipeline_runner_impl,
        )

        return _build_pipeline_runner_impl(*args, **kwargs)


__all__ = ["build_pipeline_runner"]
