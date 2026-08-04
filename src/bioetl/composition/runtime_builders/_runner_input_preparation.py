"""Private runner input preparation seams for public inputs resolver facade."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import (
    bind_cached_bronze_context as _bind_cached_bronze_context,
    resolve_exact_replay_cached_bronze_context as _resolve_exact_replay_cached_bronze_context,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    apply_tracing_override as _apply_tracing_override_impl,
)
from bioetl.composition.runtime_builders.inputs_resolution_orchestration import (
    resolve_runner_filter_config as _resolve_runner_filter_config,
    resolve_runner_runtime_config as _resolve_runner_runtime_config,
    validate_runner_data_root_policy as _validate_runner_data_root_policy,
)
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    is_critical_reproducibility_runtime,
    normalize_required_persistence_profile,
    resolve_effective_required_persistence_profile,
)

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_runtime_models import (
        ResolvedVacuumSettings,
    )
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class PreparedRunnerContext:
    settings: Settings
    effective_ctx: PipelineRunContext
    cached_bronze: CachedBronzeContext
    yaml_config: PipelineYamlConfig
    observability: ObservabilityBundle


@dataclass(frozen=True, slots=True)
class ResolvedRunnerDerivedInputs:
    runtime_config: RuntimeConfig
    filter_config: InputFilterConfig | None


def _resolve_settings_for_runner(
    *,
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
) -> Settings:
    """Apply runtime tracing overrides before building runner inputs."""
    return _apply_tracing_override_impl(
        settings=get_settings_fn(),
        enabled=getattr(ctx, "tracing_enabled_override", None),
    )


def _resolve_required_persistence_profile(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
) -> str:
    requested_profile = getattr(ctx, "required_persistence_profile", None)
    if requested_profile is not None and str(requested_profile).strip():
        return resolve_effective_required_persistence_profile(
            configured_required_profile=requested_profile,
            family_default_profile=DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
            exact_replay_requested=bool(getattr(ctx, "exact_replay", False)),
            critical_runtime=is_critical_reproducibility_runtime(
                runtime_environment=getattr(settings, "env", None),
                debug_mode=getattr(settings, "debug", False),
            ),
            allow_degraded_opt_down=(
                normalize_required_persistence_profile(requested_profile)
                == "degraded_observable"
            ),
        )
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    return normalize_required_persistence_profile(
        getattr(
            control_plane,
            "required_persistence_profile",
            DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
        )
    )


def _resolve_effective_context(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ],
) -> tuple[PipelineRunContext, CachedBronzeContext]:
    """Resolve exact-replay cached Bronze state and bind it into the context."""
    cached_bronze = _resolve_exact_replay_cached_bronze_context(
        ctx=ctx,
        settings=settings,
        cached_bronze=assemble_cached_bronze_context_fn(ctx),
    )
    return _bind_cached_bronze_context(ctx, cached_bronze), cached_bronze


def _load_runner_yaml_config(
    *,
    pipeline_name: str,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    validate_pk_contract_fn: Callable[[PipelineYamlConfig], None],
) -> PipelineYamlConfig:
    """Load and validate the pipeline contract used for runner assembly."""
    yaml_config = load_pipeline_config_fn(pipeline_name)
    validate_pk_contract_fn(yaml_config)
    return yaml_config


def _build_runner_observability(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    yaml_config: PipelineYamlConfig,
    build_observability_bundle_fn: Callable[..., ObservabilityBundle],
) -> ObservabilityBundle:
    """Create the observability bundle for one effective runner context."""
    return build_observability_bundle_fn(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
        log_level=ctx.log_level,
        yaml_config=yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
    )


def prepare_runner_context(
    *,
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    build_observability_bundle_fn: Callable[..., ObservabilityBundle],
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ],
    validate_pk_contract_fn: Callable[[PipelineYamlConfig], None],
) -> PreparedRunnerContext:
    """Resolve the shared settings/context/yaml/observability runner inputs."""
    settings = _resolve_settings_for_runner(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
    )
    _validate_runner_data_root_policy(
        ctx=ctx,
        settings=settings,
        required_persistence_profile=_resolve_required_persistence_profile(
            ctx=ctx,
            settings=settings,
        ),
    )
    effective_ctx, cached_bronze = _resolve_effective_context(
        ctx=ctx,
        settings=settings,
        assemble_cached_bronze_context_fn=assemble_cached_bronze_context_fn,
    )
    yaml_config = _load_runner_yaml_config(
        pipeline_name=ctx.pipeline_name,
        load_pipeline_config_fn=load_pipeline_config_fn,
        validate_pk_contract_fn=validate_pk_contract_fn,
    )
    observability = _build_runner_observability(
        ctx=effective_ctx,
        settings=settings,
        yaml_config=yaml_config,
        build_observability_bundle_fn=build_observability_bundle_fn,
    )
    return PreparedRunnerContext(
        settings=settings,
        effective_ctx=effective_ctx,
        cached_bronze=cached_bronze,
        yaml_config=yaml_config,
        observability=observability,
    )


def resolve_runner_derived_inputs(
    *,
    prepared: PreparedRunnerContext,
    default_health_check_mode: Literal["strict", "probe"],
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings],
    assemble_runtime_config_fn: Callable[..., RuntimeConfig],
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None],
    adjust_batch_size_for_filter_fn: Callable[..., None],
    load_source_config_fn: Callable[..., object] | None = None,
) -> ResolvedRunnerDerivedInputs:
    """Resolve runtime and filter config from one prepared runner context."""
    runtime_config = _resolve_runner_runtime_config(
        ctx=prepared.effective_ctx,
        settings=prepared.settings,
        yaml_config=prepared.yaml_config,
        observability=prepared.observability,
        default_health_check_mode=default_health_check_mode,
        assemble_vacuum_settings_fn=assemble_vacuum_settings_fn,
        assemble_runtime_config_fn=assemble_runtime_config_fn,
    )
    filter_config = _resolve_runner_filter_config(
        ctx=prepared.effective_ctx,
        settings=prepared.settings,
        yaml_config=prepared.yaml_config,
        observability=prepared.observability,
        assemble_filter_config_fn=assemble_filter_config_fn,
        adjust_batch_size_for_filter_fn=adjust_batch_size_for_filter_fn,
        load_source_config_fn=load_source_config_fn,
    )
    return ResolvedRunnerDerivedInputs(
        runtime_config=runtime_config,
        filter_config=filter_config,
    )
