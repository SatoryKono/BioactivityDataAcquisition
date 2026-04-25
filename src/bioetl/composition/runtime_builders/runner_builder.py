"""Leaf builder for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from inspect import Parameter, signature
from typing import TYPE_CHECKING, cast

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.composition import PipelineRegistry, create_registry
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.runtime_builders._runner_builder_support import (
    bind_manifest_logger_context as _bind_manifest_logger_context,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    resolve_control_plane_flags as _resolve_control_plane_flags,
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
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.ports import (
    PipelineControlPlaneArtifacts,
    PipelineCreateRunnerRequest,
)

if TYPE_CHECKING:
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        ExecutionObservabilityPort,
        PipelineFactoryPort,
        SettingsPort,
    )
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


def _create_runner_from_factory(
    *,
    factory: PipelineFactoryPort,
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> PipelineRunnerProtocol:
    request = PipelineCreateRunnerRequest(
        run_id=ctx.run_id,
        runtime=inputs.runtime_config,
        started_at=ctx.started_at,
        settings=cast("SettingsPort", inputs.settings),
        observability=cast(
            "ExecutionObservabilityPort",
            inputs.observability,
        ),
        control_plane=PipelineControlPlaneArtifacts(
            manifest_id=getattr(ctx, "manifest_id", None),
            execution_fingerprint=getattr(ctx, "execution_fingerprint", None),
            config_hash=getattr(ctx, "config_hash", None),
            resolved_config_hash=getattr(ctx, "resolved_config_hash", None),
            effective_config_hash=getattr(ctx, "effective_config_hash", None),
            dq_contract_compatibility_hash=getattr(
                ctx, "dq_contract_compatibility_hash", None
            ),
            effective_config_artifact_id=getattr(
                ctx, "effective_config_artifact_id", None
            ),
        ),
        filter_config=inputs.filter_config,
        config=inputs.yaml_config,
        cached_bronze=inputs.cached_bronze,
    )
    create_runner = factory.create_runner
    parameters = signature(create_runner).parameters.values()
    accepts_kwargs = any(
        parameter.kind == Parameter.VAR_KEYWORD for parameter in parameters
    )
    accepts_request = "request" in signature(create_runner).parameters
    if not accepts_request and accepts_kwargs:
        compatibility_create_runner = cast(
            "Callable[..., PipelineRunnerProtocol]",
            create_runner,
        )
        control_plane = request.control_plane
        return compatibility_create_runner(
            run_id=request.run_id,
            runtime=request.runtime,
            started_at=request.started_at,
            settings=request.settings,
            observability=request.observability,
            manifest_id=control_plane.manifest_id,
            execution_fingerprint=control_plane.execution_fingerprint,
            config_hash=control_plane.config_hash,
            resolved_config_hash=control_plane.resolved_config_hash,
            effective_config_hash=control_plane.effective_config_hash,
            dq_contract_compatibility_hash=(
                control_plane.dq_contract_compatibility_hash
            ),
            effective_config_artifact_id=(
                control_plane.effective_config_artifact_id
            ),
            filter_config=request.filter_config,
            config=request.config,
            cached_bronze=request.cached_bronze,
        )
    return cast("PipelineRunnerProtocol", create_runner(request))


def _resolve_optional_functions(
    build_observability_bundle_fn: Callable[..., ObservabilityBundle] | None,
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings] | None,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig] | None,
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None] | None,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ]
    | None,
) -> tuple[
    Callable[..., ObservabilityBundle],
    Callable[..., ResolvedVacuumSettings],
    Callable[..., RuntimeConfig],
    Callable[..., InputFilterConfig | None],
    Callable[[PipelineRunContext], CachedBronzeContext],
]:
    """Resolve optional function parameters to their implementations."""
    return (
        build_observability_bundle
        if build_observability_bundle_fn is None
        else build_observability_bundle_fn,
        assemble_vacuum_settings
        if assemble_vacuum_settings_fn is None
        else assemble_vacuum_settings_fn,
        assemble_runtime_config
        if assemble_runtime_config_fn is None
        else assemble_runtime_config_fn,
        assemble_filter_config
        if assemble_filter_config_fn is None
        else assemble_filter_config_fn,
        assemble_cached_bronze_context
        if assemble_cached_bronze_context_fn is None
        else assemble_cached_bronze_context_fn,
    )


def _prepare_runner_inputs_with_resolved_functions(
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    load_source_config_fn: Callable[[], object],
    resolved_functions: tuple[
        Callable[..., ObservabilityBundle],
        Callable[..., ResolvedVacuumSettings],
        Callable[..., RuntimeConfig],
        Callable[..., InputFilterConfig | None],
        Callable[[PipelineRunContext], CachedBronzeContext],
    ],
) -> _RunnerInputs:
    """Prepare runner inputs using resolved function implementations."""
    (
        build_obs_bundle,
        assemble_vacuum,
        assemble_runtime,
        assemble_filter,
        assemble_cached_bronze,
    ) = resolved_functions
    return prepare_runner_inputs(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=build_obs_bundle,
        assemble_vacuum_settings_fn=assemble_vacuum,
        assemble_runtime_config_fn=assemble_runtime,
        assemble_filter_config_fn=assemble_filter,
        assemble_cached_bronze_context_fn=assemble_cached_bronze,
        load_source_config_fn=load_source_config_fn,
    )


def _handle_control_plane_setup(
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> tuple[PipelineRunContext, _RunnerInputs, RunLedgerService | None]:
    """Handle control plane setup including manifest and ledger services."""
    manifest_enabled, ledger_enabled = _resolve_control_plane_flags(
        inputs.settings,
        yaml_config=inputs.yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
    )
    run_ledger_service: RunLedgerService | None = None

    if manifest_enabled:
        control_plane_refs, run_ledger_service = (
            create_run_manifest_with_effective_config(
                ctx=ctx,
                inputs=inputs,
                ledger_enabled=ledger_enabled,
            )
        )
        ctx = attach_manifest_id(
            ctx,
            control_plane_refs.manifest_id,
            execution_fingerprint=control_plane_refs.execution_fingerprint,
            config_hash=control_plane_refs.config_hash,
            resolved_config_hash=control_plane_refs.resolved_config_hash,
            effective_config_hash=control_plane_refs.effective_config_hash,
            dq_contract_compatibility_hash=control_plane_refs.dq_contract_compatibility_hash,
            effective_config_artifact_id=control_plane_refs.effective_config_artifact_id,
            contract_ref=control_plane_refs.contract_ref,
            contract_version=control_plane_refs.contract_version,
            contract_schema_hash=control_plane_refs.contract_schema_hash,
            dq_policy_ref=control_plane_refs.dq_policy_ref,
            rule_bundle_version=control_plane_refs.rule_bundle_version,
        )
        inputs = _bind_manifest_logger_context(
            inputs,
            control_plane_refs.manifest_id,
        )

    return ctx, inputs, run_ledger_service


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

    resolved_functions = _resolve_optional_functions(
        build_observability_bundle_fn,
        assemble_vacuum_settings_fn,
        assemble_runtime_config_fn,
        assemble_filter_config_fn,
        assemble_cached_bronze_context_fn,
    )
    inputs = _prepare_runner_inputs_with_resolved_functions(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        load_source_config_fn=load_source_config_fn,
        resolved_functions=resolved_functions,
    )
    ctx, inputs, run_ledger_service = _handle_control_plane_setup(ctx, inputs)
    runner = _create_runner_from_factory(
        factory=effective_registry.get(ctx.pipeline_name).factory,
        ctx=ctx,
        inputs=inputs,
    )
    if run_ledger_service is not None:
        attach_control_plane_collaborators(runner, run_ledger_service)
    return runner
