"""Leaf builder for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.runtime_builders._runner_builder_orchestration import (
    attach_runner_control_plane_collaborators as _attach_runner_control_plane_collaborators,
)
from bioetl.composition.runtime_builders._runner_builder_orchestration import (
    bootstrap_runner_factory as _bootstrap_runner_factory,
)
from bioetl.composition.runtime_builders._runner_builder_orchestration import (
    create_runner as _create_runner,
)
from bioetl.composition.runtime_builders.config_access import (
    get_settings as _get_settings,
)
from bioetl.composition.runtime_builders.config_access import (
    load_pipeline_config as _load_pipeline_config,
)
from bioetl.composition.runtime_builders.config_access import (
    load_source_config as _load_source_config,
)
from bioetl.composition.runtime_builders.inputs_resolver import (
    prepare_runner_inputs,
)
from bioetl.composition.runtime_builders.ledger_collaborator import (
    PipelineRunnerProtocol,
)
from bioetl.composition.runtime_builders.runner_builder_wiring import (
    RunnerBuilderWiring,
    RunnerFactoryWiring,
    RunnerInputWiring,
    resolve_runner_builder_wiring,
)
from bioetl.composition.runtime_builders.runner_input_assembly import (
    prepare_runner_context_and_inputs as _prepare_runner_context_and_inputs,
)
from bioetl.composition.runtime_builders.runner_control_plane_assembly import (
    assemble_runner_control_plane as _assemble_runner_control_plane,
)

if TYPE_CHECKING:
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.composition.runtime_builders.inputs_resolver import (
        ResolvedVacuumSettings,
    )
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        PipelineYamlConfig,
    )


__all__ = [
    "PipelineRunnerProtocol",
    "RunnerBuilderWiring",
    "RunnerFactoryWiring",
    "RunnerInputWiring",
    "build_pipeline_runner",
    "ensure_providers_loaded",
    "load_source_config",
]


_DEFAULT_RUNNER_INPUT_WIRING = RunnerInputWiring(
    get_settings=_get_settings,
    load_pipeline_config=_load_pipeline_config,
    load_source_config=_load_source_config,
)
_DEFAULT_RUNNER_BUILDER_WIRING = RunnerBuilderWiring(
    inputs=_DEFAULT_RUNNER_INPUT_WIRING,
)

load_source_config = _load_source_config


def build_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    wiring: RunnerBuilderWiring | None = None,
    factory_wiring: RunnerFactoryWiring | None = None,
    input_wiring: RunnerInputWiring | None = None,
    create_registry_fn: Callable[[], PipelineRegistry] | None = None,
    ensure_providers_loaded_fn: Callable[[], None] | None = ensure_providers_loaded,
    register_all_pipelines_fn: Callable[..., None] | None = None,
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
) -> PipelineRunnerProtocol:
    """Assemble and return a fully configured ``PipelineRunner``.

    ``wiring`` is the canonical composition seam. ``factory_wiring`` and
    ``input_wiring`` are transitional typed sub-bundles. The individual ``*_fn``
    keyword overrides are retained for focused tests and compatibility call
    sites while they migrate to the aggregate bundle.
    """
    effective_ensure_providers_loaded_fn = ensure_providers_loaded_fn
    if ensure_providers_loaded_fn is ensure_providers_loaded and (
        wiring is not None or factory_wiring is not None
    ):
        effective_ensure_providers_loaded_fn = None

    resolved_wiring = resolve_runner_builder_wiring(
        wiring or _DEFAULT_RUNNER_BUILDER_WIRING,
        factory_wiring=factory_wiring,
        input_wiring=input_wiring,
        create_registry_fn=create_registry_fn,
        ensure_providers_loaded_fn=effective_ensure_providers_loaded_fn,
        register_all_pipelines_fn=register_all_pipelines_fn,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        load_source_config_fn=load_source_config_fn,
        build_observability_bundle_fn=build_observability_bundle_fn,
        assemble_vacuum_settings_fn=assemble_vacuum_settings_fn,
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        assemble_filter_config_fn=assemble_filter_config_fn,
        assemble_cached_bronze_context_fn=assemble_cached_bronze_context_fn,
    )
    factory_wiring = resolved_wiring.factory
    input_wiring = resolved_wiring.inputs
    factory_bootstrap = _bootstrap_runner_factory(
        pipeline_name=ctx.pipeline_name,
        registry=registry,
        create_registry_fn=factory_wiring.create_registry,
        ensure_providers_loaded_fn=factory_wiring.ensure_providers_loaded,
        register_all_pipelines_fn=factory_wiring.register_all_pipelines,
    )

    ctx, inputs = _prepare_runner_context_and_inputs(
        ctx=ctx,
        get_settings_fn=input_wiring.get_settings,
        load_pipeline_config_fn=input_wiring.load_pipeline_config,
        load_source_config_fn=input_wiring.load_source_config,
        build_observability_bundle_fn=input_wiring.build_observability_bundle,
        assemble_vacuum_settings_fn=input_wiring.assemble_vacuum_settings,
        assemble_runtime_config_fn=input_wiring.assemble_runtime_config,
        assemble_filter_config_fn=input_wiring.assemble_filter_config,
        assemble_cached_bronze_context_fn=input_wiring.assemble_cached_bronze_context,
        prepare_runner_inputs_fn=prepare_runner_inputs,
    )
    control_plane_setup = _assemble_runner_control_plane(ctx, inputs)
    runner = _create_runner(
        factory=factory_bootstrap.factory,
        ctx=control_plane_setup.ctx,
        inputs=control_plane_setup.inputs,
    )
    _attach_runner_control_plane_collaborators(
        runner=runner,
        required_profile=control_plane_setup.required_profile,
        run_ledger_service=control_plane_setup.run_ledger_service,
    )
    return runner
