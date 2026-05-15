"""Leaf builder for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders._runner_builder_support import (
    bind_manifest_logger_context as _bind_manifest_logger_context,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    resolve_runner_control_plane_policy as _resolve_runner_control_plane_policy,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    validate_artifact_recorder_attachment as _validate_artifact_recorder_attachment,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    validate_strict_data_root_policy as _validate_strict_data_root_policy,
)
from bioetl.composition.runtime_builders._runner_factory_compat import (
    create_runner_from_factory as _create_runner_from_factory,
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
    attach_control_plane_collaborators,
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


def _initialize_registry(
    *,
    registry: PipelineRegistry | None,
    create_registry_fn: Callable[[], PipelineRegistry],
    ensure_providers_loaded_fn: Callable[[], None],
    register_all_pipelines_fn: Callable[..., None],
) -> PipelineRegistry:
    """Initialize provider/pipeline registry with optional explicit registry."""
    effective_registry = registry if registry is not None else create_registry_fn()
    ensure_providers_loaded_fn()
    register_all_pipelines_fn(registry=effective_registry)
    return effective_registry


def _handle_control_plane_setup(
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> tuple[PipelineRunContext, _RunnerInputs, RunLedgerService | None, str]:
    """Handle control plane setup including manifest and ledger services."""
    control_plane_policy = _resolve_runner_control_plane_policy(
        inputs.settings,
        yaml_config=inputs.yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
    )
    _validate_strict_data_root_policy(
        settings=inputs.settings,
        required_profile=control_plane_policy.required_profile,
        exact_replay=bool(getattr(ctx, "exact_replay", False)),
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

    return ctx, inputs, run_ledger_service, effective_required_profile


def _create_runner(
    *,
    registry: PipelineRegistry,
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> PipelineRunnerProtocol:
    """Create the runtime runner from the registered factory seam."""
    factory = registry.get(ctx.pipeline_name).factory
    return _create_runner_from_factory(
        factory=factory,
        ctx=ctx,
        inputs=inputs,
    )


def _attach_runner_control_plane_collaborators(
    *,
    runner: PipelineRunnerProtocol,
    required_profile: str,
    run_ledger_service: RunLedgerService | None,
) -> None:
    """Attach optional control-plane collaborators and validate closure."""
    if run_ledger_service is None:
        return
    attachment_result = attach_control_plane_collaborators(
        runner,
        run_ledger_service,
    )
    _validate_artifact_recorder_attachment(
        required_profile=required_profile,
        candidate_count=attachment_result.candidate_count,
        attached_count=attachment_result.attached_count,
        missing_attach_method_count=(attachment_result.missing_attach_method_count),
        failed_count=attachment_result.failed_count,
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
    """Assemble and return a fully configured ``PipelineRunner``.

    Args:
        ctx: Pipeline run context containing pipeline name, run type, and execution options.
        registry: Optional PipelineRegistry for test isolation; creates a fresh
            runtime registry when None.
        create_registry_fn: Callable returning a fresh PipelineRegistry instance.
        ensure_providers_loaded_fn: Callable ensuring provider adapters are loaded.
        register_all_pipelines_fn: Callable registering all pipeline factories.
        get_settings_fn: Callable returning global application Settings.
        load_pipeline_config_fn: Callable loading PipelineYamlConfig by pipeline name.
        build_observability_bundle_fn: Optional callable returning an ObservabilityBundle.
            Uses the canonical observability builder when omitted.
        assemble_vacuum_settings_fn: Optional callable merging CLI and YAML vacuum
            settings. Uses the canonical runtime input resolver when omitted.
        assemble_runtime_config_fn: Optional callable building RuntimeConfig from
            context. Uses the canonical runtime input resolver when omitted.
        assemble_filter_config_fn: Optional callable building InputFilterConfig from
            YAML and CLI. Uses the canonical runtime input resolver when omitted.
        assemble_cached_bronze_context_fn: Optional callable resolving cached bronze
            context. Uses the canonical runtime input resolver when omitted.

    Returns:
        Fully configured PipelineRunner ready for execution.
    """
    effective_registry = _initialize_registry(
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
    ctx, inputs, run_ledger_service, required_profile = _handle_control_plane_setup(
        ctx,
        inputs,
    )
    runner = _create_runner(
        registry=effective_registry,
        ctx=ctx,
        inputs=inputs,
    )
    _attach_runner_control_plane_collaborators(
        runner=runner,
        required_profile=required_profile,
        run_ledger_service=run_ledger_service,
    )
    return runner
