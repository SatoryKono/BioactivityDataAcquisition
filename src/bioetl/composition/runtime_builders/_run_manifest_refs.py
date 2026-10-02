"""Control-plane ref helpers for manifest builders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._run_manifest_context_updates import (
    build_contract_identity_field_values,
    build_control_plane_identity_ref_values,
)
from bioetl.composition.runtime_builders.input_snapshot_resolution import (
    resolve_cached_bronze_input_snapshot_refs,
    resolve_pipeline_input_snapshot_refs,
)
from bioetl.domain.control_plane import RunSourceRef
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
    require_input_snapshots,
)

if TYPE_CHECKING:
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings


def build_run_source_refs(
    *,
    ctx: PipelineRunContext,
    cached_bronze: CachedBronzeContext | None,
    settings: Settings,
    provider: str,
    entity: str,
    required_persistence_profile: object = DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
) -> tuple[RunSourceRef, ...]:
    """Build source references and enforce strict snapshot persistence."""
    cached_bronze_enabled = cached_bronze is not None and bool(
        getattr(cached_bronze, "enabled", False)
    )
    strict_require = bool(getattr(ctx, "exact_replay", False)) or (
        normalize_required_persistence_profile(required_persistence_profile)
        in STRICT_PERSISTENCE_PROFILES
    )
    if cached_bronze_enabled:
        # Strict runs fail here with the cached-bronze provenance message;
        # degraded_observable defers to the post-persist manifest gate so the
        # audit trail still lands (see _publish_manifest_and_refs).
        input_snapshots = resolve_cached_bronze_input_snapshot_refs(
            cached_bronze=cached_bronze,
            settings=settings,
            provider=provider,
            entity=entity,
            require=strict_require,
        )
    else:
        input_snapshots = resolve_pipeline_input_snapshot_refs(
            ctx=ctx,
            cached_bronze=cached_bronze,
            settings=settings,
            provider=provider,
            entity=entity,
        )
    if not (cached_bronze_enabled and not input_snapshots):
        require_input_snapshots(
            exact_replay=bool(getattr(ctx, "exact_replay", False)),
            required_persistence_profile=required_persistence_profile,
            input_snapshots=input_snapshots,
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


@dataclass(frozen=True, slots=True)
class ManifestControlPlaneRefs:
    """Resolved control-plane references produced before factory runner wiring."""

    manifest_id: str
    execution_fingerprint: str | None
    config_hash: str | None
    resolved_config_hash: str | None
    effective_config_hash: str | None
    source_fingerprint: str | None
    dq_contract_compatibility_hash: str | None
    effective_config_artifact_id: str | None
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    input_snapshot_fingerprint: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    normalization_profile_ref: str | None = None
    normalization_profile_version: str | None = None
    normalization_profile_hash: str | None = None
    required_persistence_profile: str | None = None


def create_control_plane_refs(
    *,
    manifest_id: str,
    execution_fingerprint: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    source_fingerprint: str | None,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    replay_parentage: tuple[str | None, str | None] = (None, None),
    input_snapshot_fingerprint: str | None = None,
    contract: tuple[str | None, str | None, str | None] = (None, None, None),
    policy: tuple[str | None, str | None] = (None, None),
    normalization_profile: tuple[str | None, str | None, str | None] = (
        None,
        None,
        None,
    ),
    required_persistence_profile: str | None = None,
) -> ManifestControlPlaneRefs:
    """Build the compact control-plane refs bundle returned to callers.

    Packed groups under Sonar S107:
    - ``replay_parentage``: ``(replay_of_run_id, replay_of_manifest_id)``
    - ``contract``: ``(contract_ref, contract_version, contract_schema_hash)``
    - ``policy``: ``(dq_policy_ref, rule_bundle_version)``
    - ``normalization_profile``: ``(ref, version, hash)``
    """
    replay_of_run_id, replay_of_manifest_id = replay_parentage
    contract_ref, contract_version, contract_schema_hash = contract
    dq_policy_ref, rule_bundle_version = policy
    (
        normalization_profile_ref,
        normalization_profile_version,
        normalization_profile_hash,
    ) = normalization_profile
    contract_identity_values = build_contract_identity_field_values(
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
        normalization_profile_ref=normalization_profile_ref,
        normalization_profile_version=normalization_profile_version,
        normalization_profile_hash=normalization_profile_hash,
    )
    return ManifestControlPlaneRefs(
        manifest_id=manifest_id,
        execution_fingerprint=execution_fingerprint,
        config_hash=resolved_config_hash,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        **build_control_plane_identity_ref_values(
            contract_identity_values=contract_identity_values,
            required_persistence_profile=required_persistence_profile,
        ),
    )
