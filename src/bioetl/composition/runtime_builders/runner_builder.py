"""Leaf builder for runtime pipeline runner construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.bootstrap.service_registry_contracts import (
    PipelineRunnerProtocol,
)
from bioetl.composition.runtime_builders._runner_builder_orchestration import (
    attach_runner_control_plane_collaborators as _attach_runner_control_plane_collaborators,
    bootstrap_runner_factory as _bootstrap_runner_factory,
    create_runner as _create_runner,
)
from bioetl.composition.runtime_builders.config_access import (
    load_source_config as _load_source_config,
)
from bioetl.composition.runtime_builders.inputs_resolver import prepare_runner_inputs
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
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.context import PipelineRunContext

__all__ = [
    "PipelineRunnerProtocol",
    "RunnerBuilderWiring",
    "RunnerFactoryWiring",
    "RunnerInputWiring",
    "build_pipeline_runner",
    "ensure_providers_loaded",
    "load_source_config",
]

load_source_config = _load_source_config


def build_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    wiring: RunnerBuilderWiring | None = None,
) -> PipelineRunnerProtocol:
    """Assemble and return a fully configured ``PipelineRunner``."""
    resolved_wiring = resolve_runner_builder_wiring(wiring)
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
