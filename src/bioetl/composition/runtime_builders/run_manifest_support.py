"""Support helpers for constructing run manifest payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders.input_snapshot_resolution import (
    resolve_pipeline_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    ManifestControlPlaneRefs,
    build_planned_artifacts,
    control_plane_root,
    create_control_plane_refs,
)
from bioetl.composition.runtime_builders._run_manifest_context_updates import (
    apply_manifest_updates_to_mutable_context,
    build_dataclass_manifest_updates,
    extract_optional_updates_from_refs,
    iter_optional_control_plane_updates,
    iter_optional_control_plane_updates_from_mapping,
)
from bioetl.composition.runtime_builders._run_context_values import (
    resolve_run_context_values,
)
from bioetl.composition.runtime_builders._run_manifest_sink_policy import (
    validate_reproducible_sink_modes,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    build_launch_context_snapshot,
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
    resolve_replay_capability as _resolve_policy_replay_capability,
)

if TYPE_CHECKING:
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "ManifestControlPlaneRefs",
    "RunManifestContractIdentity",
    "RunManifestProvenanceBundle",
    "apply_manifest_updates_to_mutable_context",
    "build_dataclass_manifest_updates",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_manifest_provenance_bundle",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "extract_optional_updates_from_refs",
    "iter_optional_control_plane_updates",
    "iter_optional_control_plane_updates_from_mapping",
    "resolve_contract_identity",
    "resolve_provider_entity",
    "resolve_replay_capability",
    "resolve_replay_parentage",
    "resolve_run_context_values",
    "to_serializable_mapping",
    "validate_reproducible_sink_modes",
]


@dataclass(frozen=True, slots=True)
class RunManifestProvenanceBundle:
    """Effective-config provenance bundle passed into manifest creation."""

    effective_config_artifact_id: str
    resolved_config_hash: str
    effective_config_hash: str
    source_fingerprint: str | None
    dq_contract_compatibility_hash: str


def build_run_manifest_provenance_bundle(
    artifact_result: tuple[str, str, str, str | None, str],
) -> RunManifestProvenanceBundle:
    """Convert one persisted effective-config result tuple into manifest provenance."""
    (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        source_fingerprint,
        dq_contract_compatibility_hash,
    ) = artifact_result
    return RunManifestProvenanceBundle(
        effective_config_artifact_id=effective_config_artifact_id,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
    )


def build_run_source_refs(
    *,
    ctx: PipelineRunContext,
    cached_bronze: CachedBronzeContext | None,
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
