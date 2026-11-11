"""Snapshot launch-context helpers for run manifest construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._runtime_launch_context_fields import (
    build_runtime_launch_field_snapshot,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_resolution import (
    resolve_name_component,
)
from bioetl.composition.services.effective_config_serializer import (
    to_serializable_mapping as to_serializable_mapping,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    archive_policy_for_persistence_profile,
)
from bioetl.domain.runtime.composition_boundary_policy import (
    pipeline_name_fallbacks,
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
    snapshot = build_runtime_launch_field_snapshot(
        ctx,
        run_type_value=run_type_value,
        execution_context_value=execution_context_value,
    )
    snapshot.update(
        {
            "configured_required_persistence_profile": (
                configured_required_persistence_profile or required_persistence_profile
            ),
            "required_persistence_profile": required_persistence_profile,
            "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        }
    )
    if required_persistence_profile_opt_down:
        snapshot["required_persistence_profile_opt_down"] = True
    archive_policy = archive_policy_for_persistence_profile(
        required_persistence_profile
    )
    if archive_policy is not None:
        snapshot["archive_policy"] = archive_policy
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


def resolve_provider_entity(
    *,
    pipeline_name: str,
    yaml_config: object,
) -> tuple[str, str]:
    """Resolve provider and entity from pipeline name and config."""
    fallback_provider, fallback_entity = _determine_fallbacks(pipeline_name)
    provider = _resolve_config_name(
        yaml_config,
        attribute_name="provider",
        fallback=fallback_provider,
    )
    entity = _resolve_config_name(
        yaml_config,
        attribute_name="entity_type",
        fallback=fallback_entity,
    )
    return provider, entity


def _determine_fallbacks(pipeline_name: str) -> tuple[str, str]:
    """Determine fallback provider and entity from pipeline name."""

    return pipeline_name_fallbacks(pipeline_name)


def _resolve_config_name(
    yaml_config: object,
    *,
    attribute_name: str,
    fallback: str,
) -> str:
    """Resolve one config name component or use the pipeline-name fallback."""
    return resolve_name_component(
        getattr(yaml_config, attribute_name, None),
        fallback=fallback,
    )
