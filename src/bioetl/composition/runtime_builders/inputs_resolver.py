"""Public runtime input resolver facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._runner_input_preparation import (
    prepare_runner_context as _prepare_runner_context,
)
from bioetl.composition.runtime_builders._runner_input_preparation import (
    resolve_runner_derived_inputs as _resolve_runner_derived_inputs,
)
from bioetl.composition.runtime_builders import (
    inputs_runtime_assembly as _runtime_assembly,
)
from bioetl.composition.runtime_builders.config_access import (
    load_source_config as _load_source_config,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    log_cached_bronze as _log_cached_bronze,
)
from bioetl.composition.runtime_builders.inputs_runtime_models import (
    ResolvedVacuumSettings,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.composition.observability import ObservabilityBundle
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


@dataclass(frozen=True, slots=True)
class RunnerInputs:
    settings: Settings
    yaml_config: PipelineYamlConfig
    observability: ObservabilityBundle
    runtime_config: RuntimeConfig
    filter_config: InputFilterConfig | None
    cached_bronze: CachedBronzeContext


adjust_batch_size_for_filter = _runtime_assembly.adjust_batch_size_for_filter
assemble_cached_bronze_context = _runtime_assembly.assemble_cached_bronze_context
assemble_filter_config = _runtime_assembly.assemble_filter_config
assemble_runtime_config = _runtime_assembly.assemble_runtime_config
assemble_vacuum_settings = _runtime_assembly.assemble_vacuum_settings
resolve_filter_batch_size = _runtime_assembly.resolve_filter_batch_size
resolve_health_check_mode = _runtime_assembly.resolve_health_check_mode
validate_pk_contract = _runtime_assembly.validate_pk_contract


__all__ = [
    "ResolvedVacuumSettings",
    "RunnerInputs",
    "prepare_runner_inputs",
    "resolve_health_check_mode",
]


def prepare_runner_inputs(
    *,
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    build_observability_bundle_fn: Callable[..., ObservabilityBundle],
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings],
    assemble_runtime_config_fn: Callable[..., RuntimeConfig],
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None],
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ],
    load_source_config_fn: Callable[..., object] | None = None,
) -> RunnerInputs:
    source_config_loader = (
        _load_source_config
        if load_source_config_fn is None
        else load_source_config_fn
    )
    prepared = _prepare_runner_context(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=build_observability_bundle_fn,
        assemble_cached_bronze_context_fn=assemble_cached_bronze_context_fn,
        validate_pk_contract_fn=validate_pk_contract,
    )
    derived_inputs = _resolve_runner_derived_inputs(
        prepared=prepared,
        default_health_check_mode="strict",
        assemble_vacuum_settings_fn=assemble_vacuum_settings_fn,
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        assemble_filter_config_fn=assemble_filter_config_fn,
        adjust_batch_size_for_filter_fn=adjust_batch_size_for_filter,
        load_source_config_fn=source_config_loader,
    )
    _log_cached_bronze(
        observability=prepared.observability,
        cached_bronze=prepared.cached_bronze,
    )
    return RunnerInputs(
        settings=prepared.settings,
        yaml_config=prepared.yaml_config,
        observability=prepared.observability,
        runtime_config=derived_inputs.runtime_config,
        filter_config=derived_inputs.filter_config,
        cached_bronze=prepared.cached_bronze,
    )
