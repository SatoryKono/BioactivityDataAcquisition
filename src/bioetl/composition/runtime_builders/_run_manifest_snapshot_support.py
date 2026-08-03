"""Snapshot launch-context helpers for run manifest construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._runtime_launch_context_fields import (
    build_runtime_launch_field_snapshot,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_resolution import (
    as_runtime_config_mapping,
    coerce_optional_text,
    resolve_name_component,
    resolve_replay_parentage_mapping_value,
)
from bioetl.composition.runtime_builders._snapshot_mapping_support import (
    to_serializable_mapping as to_serializable_mapping,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext


def build_launch_context_snapshot(
    ctx: PipelineRunContext,
    *,
    run_type_value: str,
    execution_context_value: str,
    configured_required_persistence_profile: str | None = None,
    required_persistence_profile: str,
    required_persistence_profile_opt_down: bool = False,
    strict_exact_replay_supported: bool | None = None,
    reproducibility_family: str | None = None,
    replay_family_contract: str | None = None,
    strict_replay_runtime_verdict: str | None = None,
    replay_support_scope: str | None = None,
    replay_support_reason: str | None = None,
) -> dict[str, object]:
    """Build a snapshot of the launch context."""
    snapshot = _build_base_snapshot(ctx, run_type_value, execution_context_value)
    exact_replay_support_boundary = _determine_replay_support_boundary()
    snapshot.update(
        {
            "configured_required_persistence_profile": (
                configured_required_persistence_profile or required_persistence_profile
            ),
            "required_persistence_profile": required_persistence_profile,
            "exact_replay_support_boundary": exact_replay_support_boundary,
        }
    )
    if required_persistence_profile_opt_down:
        snapshot["required_persistence_profile_opt_down"] = True
    _add_reproducibility_profile_fields(
        snapshot,
        strict_exact_replay_supported=strict_exact_replay_supported,
        reproducibility_family=reproducibility_family,
        replay_family_contract=replay_family_contract,
        strict_replay_runtime_verdict=strict_replay_runtime_verdict,
        replay_support_scope=replay_support_scope,
        replay_support_reason=replay_support_reason,
    )
    _add_optional_fields(snapshot, ctx)
    return snapshot


def _build_base_snapshot(
    ctx: PipelineRunContext,
    run_type_value: str,
    execution_context_value: str,
) -> dict[str, object]:
    """Build the base snapshot."""
    return build_runtime_launch_field_snapshot(
        ctx,
        run_type_value=run_type_value,
        execution_context_value=execution_context_value,
    )


def _determine_replay_support_boundary() -> str:
    """Determine the replay support boundary."""
    return "snapshot_backed_source_runs_only"


def _add_reproducibility_profile_fields(
    snapshot: dict[str, object],
    *,
    strict_exact_replay_supported: bool | None,
    reproducibility_family: str | None,
    replay_family_contract: str | None,
    strict_replay_runtime_verdict: str | None,
    replay_support_scope: str | None,
    replay_support_reason: str | None,
) -> None:
    """Attach explicit replay-support metadata when the profile is resolved."""
    if strict_exact_replay_supported is not None:
        snapshot["strict_exact_replay_supported"] = strict_exact_replay_supported
    optional_fields = {
        "reproducibility_family": reproducibility_family,
        "replay_family_contract": replay_family_contract,
        "strict_replay_runtime_verdict": strict_replay_runtime_verdict,
        "replay_support_scope": replay_support_scope,
        "replay_support_reason": replay_support_reason,
    }
    snapshot.update(
        {key: value for key, value in optional_fields.items() if value is not None}
    )


def _add_optional_fields(snapshot: dict[str, object], ctx: PipelineRunContext) -> None:
    """Add optional fields to the snapshot."""
    snapshot["vacuum"] = to_serializable_mapping(getattr(ctx, "vacuum", None))
    snapshot["input_filter"] = to_serializable_mapping(
        getattr(ctx, "input_filter", None)
    )
    snapshot["cached_bronze"] = to_serializable_mapping(
        getattr(ctx, "cached_bronze", None)
    )


def resolve_replay_parentage(
    *,
    ctx: PipelineRunContext,
    runtime_config: object,
) -> tuple[str | None, str | None]:
    """Resolve the replay parentage."""
    runtime_config_mapping = as_runtime_config_mapping(runtime_config)
    replay_of_run_id = _resolve_replay_id(
        ctx, "replay_of_run_id", runtime_config_mapping
    )
    replay_of_manifest_id = _resolve_replay_id(
        ctx, "replay_of_manifest_id", runtime_config_mapping
    )
    return replay_of_run_id, replay_of_manifest_id


def _resolve_replay_id(
    ctx: PipelineRunContext,
    attr_name: str,
    runtime_config_mapping: object,
) -> str | None:
    """Resolve the replay ID from context or runtime config."""
    ctx_value = coerce_optional_text(getattr(ctx, attr_name, None))
    if ctx_value is not None:
        return ctx_value

    keys = (attr_name, f"exact_replay_parent_{attr_name}")
    return resolve_replay_parentage_mapping_value(
        as_runtime_config_mapping(runtime_config_mapping),
        *keys,
    )


def resolve_provider_entity(
    *,
    pipeline_name: str,
    yaml_config: object,
) -> tuple[str, str]:
    """Resolve provider and entity from pipeline name and config."""
    fallback_provider, fallback_entity = _determine_fallbacks(pipeline_name)
    provider = _resolve_provider(yaml_config, fallback_provider)
    entity = _resolve_entity(yaml_config, fallback_entity)
    return provider, entity


def _determine_fallbacks(pipeline_name: str) -> tuple[str, str]:
    """Determine fallback provider and entity from pipeline name."""
    if "_" in pipeline_name:
        provider, entity = pipeline_name.split("_", 1)
        return provider, entity
    return pipeline_name, pipeline_name


def _resolve_provider(yaml_config: object, fallback: str) -> str:
    """Resolve provider from config or use fallback."""
    return resolve_name_component(
        getattr(yaml_config, "provider", None),
        fallback=fallback,
    )


def _resolve_entity(yaml_config: object, fallback: str) -> str:
    """Resolve entity from config or use fallback."""
    return resolve_name_component(
        getattr(yaml_config, "entity_type", None),
        fallback=fallback,
    )
