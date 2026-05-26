"""Support helpers for constructing run manifest payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._input_snapshot_resolution import (
    resolve_pipeline_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    ManifestControlPlaneRefs,
    build_planned_artifacts,
    control_plane_root,
    create_control_plane_refs,
    legacy_config_hash_from_resolved_config_hash,
    resolve_run_context_values,
)
from bioetl.composition.runtime_builders._run_manifest_sink_policy import (
    validate_reproducible_sink_modes,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    build_launch_context_snapshot,
    normalize_snapshot,
    resolve_provider_entity,
    resolve_replay_parentage,
    to_serializable_mapping,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    RunManifestContractIdentity,
    resolve_contract_identity,
)
from bioetl.domain.control_plane import ReplayCapability, RunSourceRef
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    resolve_replay_capability as _resolve_policy_replay_capability,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "ManifestControlPlaneRefs",
    "RunManifestContractIdentity",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "legacy_config_hash_from_resolved_config_hash",
    "normalize_snapshot",
    "resolve_contract_identity",
    "resolve_provider_entity",
    "resolve_replay_capability",
    "resolve_replay_parentage",
    "resolve_run_context_values",
    "to_serializable_mapping",
    "validate_reproducible_sink_modes",
]


def build_run_source_refs(
    *,
    ctx: PipelineRunContext,
    cached_bronze: object | None,
    settings: Settings,
    provider: str,
    entity: str,
    required_persistence_profile: object = DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
) -> tuple[RunSourceRef, ...]:
    input_snapshots = resolve_pipeline_input_snapshot_refs(
        ctx=ctx,
        cached_bronze=cached_bronze,
        settings=settings,
        provider=provider,
        entity=entity,
    )
    required_profile = normalize_required_persistence_profile(
        required_persistence_profile
    )
    strict_snapshot_required = bool(getattr(ctx, "exact_replay", False)) or (
        required_profile in STRICT_PERSISTENCE_PROFILES
    )
    if strict_snapshot_required and not input_snapshots:
        raise RuntimeError(
            "Exact replay and strict persistence profiles require immutable "
            "input snapshots; no snapshot-backed source refs were resolved "
            f"for required persistence profile '{required_profile}'"
        )
    return (
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=ctx.pipeline_name,
            query=getattr(ctx, "query", None),
            input_snapshots=input_snapshots,
        ),
    )


def resolve_replay_capability(
    *,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
) -> ReplayCapability:
    return _resolve_policy_replay_capability(
        source_refs=source_refs,
        resume_requested=resume_requested,
    )
