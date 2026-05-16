"""Leaf builder for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders._runner_builder_orchestration import (
    attach_runner_control_plane_collaborators as _attach_runner_control_plane_collaborators,
)
from bioetl.composition.runtime_builders._runner_builder_orchestration import (
    bootstrap_runner_factory as _bootstrap_runner_factory,
)
from bioetl.composition.runtime_builders._runner_builder_orchestration import (
    create_runner as _create_runner,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    bind_manifest_logger_context as _bind_manifest_logger_context,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    resolve_runner_control_plane_policy as _resolve_runner_control_plane_policy,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    validate_strict_data_root_policy as _validate_strict_data_root_policy,
)
from bioetl.composition.runtime_builders.config_access import (
    get_settings,
    load_pipeline_config,
    load_source_config,
)
from bioetl.composition.runtime_builders.control_plane import (
    attach_manifest_id,
    create_run_manifest_with_effective_config,
)
from bioetl.composition.runtime_builders.inputs_resolver import (
    ResolvedVacuumSettings,
    assemble_cached_bronze_context,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
    prepare_runner_inputs,
)
from bioetl.composition.runtime_builders.inputs_resolver import (
    RunnerInputs as _RunnerInputs,
)
from bioetl.composition.runtime_builders.ledger_collaborator import (
    PipelineRunnerProtocol,
)
from bioetl.composition.runtime_builders.observability_builder import (
    build_observability_bundle,
)
from bioetl.composition.runtime_builders.runner_input_assembly import (
    prepare_runner_context_and_inputs as _prepare_runner_context_and_inputs,
)
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        PipelineYamlConfig,
    )


__all__ = ["PipelineRunnerProtocol", "build_pipeline_runner"]


@dataclass(frozen=True, slots=True)
class _ControlPlaneSetupResult:
    ctx: PipelineRunContext
    inputs: _RunnerInputs
    run_ledger_service: RunLedgerService | None
    required_profile: str


def _handle_control_plane_setup(
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> _ControlPlaneSetupResult:
    """Handle control plane setup including manifest and ledger services."""
    control_plane_policy = _resolve_runner_control_plane_policy(
        inputs.settings,
        yaml_config=inputs.yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
        required_profile_override=getattr(ctx, "required_persistence_profile", None),
        exact_replay=bool(getattr(ctx, "exact_replay", False)),
    )
    _validate_strict_data_root_policy(
        settings=inputs.settings,
        required_profile=control_plane_policy.required_profile,
        exact_replay=bool(getattr(ctx, "exact_replay", False)),
    )
    ctx = replace(
        ctx,
        required_persistence_profile=control_plane_policy.required_profile,
    )
    run_ledger_service: RunLedgerService | None = None

    effective_required_profile = control_plane_policy.required_profile
    if control_plane_policy.manifest_enabled:
        control_plane_refs, run_ledger_service = (
            create_run_manifest_with_effective_config(
                ctx=ctx,
                inputs=inputs,
                ledger_enabled=control_plane_policy.ledger_enabled,
            )
        )
        ctx = attach_manifest_id(
            ctx,
            control_plane_refs=control_plane_refs,
        )
        inputs = _bind_manifest_logger_context(
            inputs,
            control_plane_refs.manifest_id,
        )
        effective_required_profile = (
            control_plane_refs.required_persistence_profile
            or control_plane_policy.required_profile
        )

    return _ControlPlaneSetupResult(
        ctx=ctx,
        inputs=inputs,
        run_ledger_service=run_ledger_service,
        required_profile=effective_required_profile,
    )
def build_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    create_registry_fn: Callable[[], PipelineRegistry] = create_registry,
    ensure_providers_loaded_fn: Callable[[], None] = ensure_providers_loaded,
    register_all_pipelines_fn: Callable[..., None] = register_all_pipelines,
    get_settings_fn: Callable[[], Settings] = get_settings,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] = load_pipeline_config,
    load_source_config_fn: Callable[..., object] = load_source_config,
    build_observability_bundle_fn: Callable[..., ObservabilityBundle] | None = None,
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings] | None = None,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig] | None = None,
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None] | None = None,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ]
    | None = None,
) -> PipelineRunnerProtocol:
    """Assemble and return a fully configured ``PipelineRunner``."""
    factory_bootstrap = _bootstrap_runner_factory(
        pipeline_name=ctx.pipeline_name,
        registry=registry,
        create_registry_fn=create_registry_fn,
        ensure_providers_loaded_fn=ensure_providers_loaded_fn,
        register_all_pipelines_fn=register_all_pipelines_fn,
    )

    ctx, inputs = _prepare_runner_context_and_inputs(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        load_source_config_fn=load_source_config_fn,
        build_observability_bundle_fn=build_observability_bundle
        if build_observability_bundle_fn is None
        else build_observability_bundle_fn,
        assemble_vacuum_settings_fn=assemble_vacuum_settings
        if assemble_vacuum_settings_fn is None
        else assemble_vacuum_settings_fn,
        assemble_runtime_config_fn=assemble_runtime_config
        if assemble_runtime_config_fn is None
        else assemble_runtime_config_fn,
        assemble_filter_config_fn=assemble_filter_config
        if assemble_filter_config_fn is None
        else assemble_filter_config_fn,
        assemble_cached_bronze_context_fn=assemble_cached_bronze_context
        if assemble_cached_bronze_context_fn is None
        else assemble_cached_bronze_context_fn,
        prepare_runner_inputs_fn=prepare_runner_inputs,
    )
    control_plane_setup = _handle_control_plane_setup(ctx, inputs)
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
