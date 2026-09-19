"""Runner input assembly helpers for the runtime runner builder."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import is_dataclass, replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from bioetl.composition.lazy_exports import resolve_lazy_callable
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders.inputs_runtime_assembly import (
    ResolvedVacuumSettings,
    adjust_batch_size_for_filter,
    assemble_cached_bronze_context,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
    validate_pk_contract,
)
from bioetl.composition.runtime_builders.inputs_resolver import prepare_runner_inputs
from bioetl.composition.runtime_builders.runner_inputs import (
    RunnerInputs as _RunnerInputs,
)
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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
    resolved_observability_bundle: Callable[..., ObservabilityBundle] = (
        resolve_lazy_callable(
            "bioetl.composition.runtime_builders.observability_builder",
            "build_observability_bundle",
        )
        if build_observability_bundle_fn is None
        else build_observability_bundle_fn
    )

    return (
        resolved_observability_bundle,
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
    load_source_config_fn: Callable[..., object],
    prepare_runner_inputs_fn: Callable[..., _RunnerInputs],
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
    return prepare_runner_inputs_fn(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=build_obs_bundle,
        assemble_vacuum_settings_fn=assemble_vacuum,
        assemble_runtime_config_fn=assemble_runtime,
        assemble_filter_config_fn=assemble_filter,
        assemble_cached_bronze_context_fn=assemble_cached_bronze,
        load_source_config_fn=load_source_config_fn,
        validate_pk_contract_fn=validate_pk_contract,
        adjust_batch_size_for_filter_fn=adjust_batch_size_for_filter,
    )


def _bind_resolved_cached_bronze_context[T](
    ctx: T,
    inputs: _RunnerInputs,
) -> T:
    """Propagate resolved cached Bronze replay context back into the run context."""
    current = getattr(ctx, "cached_bronze", None)
    resolved = inputs.cached_bronze
    if current == resolved:
        return ctx
    if is_dataclass(ctx):
        return cast("T", replace(cast("Any", ctx), cached_bronze=resolved))
    payload = dict(vars(ctx))
    payload["cached_bronze"] = resolved
    return cast("T", SimpleNamespace(**payload))


def prepare_runner_context_and_inputs(
    *,
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    load_source_config_fn: Callable[..., object],
    build_observability_bundle_fn: Callable[..., ObservabilityBundle] | None,
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings] | None,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig] | None,
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None] | None,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ]
    | None,
    prepare_runner_inputs_fn: Callable[..., _RunnerInputs] = prepare_runner_inputs,
) -> tuple[PipelineRunContext, _RunnerInputs]:
    """Resolve runner input collaborators and bind their effective context."""
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
        prepare_runner_inputs_fn=prepare_runner_inputs_fn,
        resolved_functions=resolved_functions,
    )
    return _bind_resolved_cached_bronze_context(ctx, inputs), inputs
