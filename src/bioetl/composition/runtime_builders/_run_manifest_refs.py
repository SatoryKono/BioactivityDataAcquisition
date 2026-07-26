"""Control-plane ref helpers for manifest builders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._run_manifest_data_roots import (
    DataRootMode as DataRootMode,
    is_explicit_data_root_configured as is_explicit_data_root_configured,
    resolve_data_root_mode as resolve_data_root_mode,
)
from bioetl.composition.runtime_builders._run_manifest_identity_ref_values import (
    build_contract_identity_field_values,
    build_control_plane_identity_ref_values,
)


if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunArtifactRef
    from bioetl.infrastructure.config.settings_api import Settings


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Typed forwarding wrapper for the control-plane root helper."""
    from bioetl.composition.runtime_builders._run_manifest_control_plane_paths import (
        control_plane_root as impl,
    )

    return impl(settings, leaf)


def build_planned_artifacts(
    *,
    settings: Settings,
    provider: str,
    entity: str,
    run_id: str | None = None,
    pipeline_name: str | None = None,
    workflow_id: str = "standalone",
    debug_export_root: str | None = None,
) -> tuple[RunArtifactRef, ...]:
    """Typed forwarding wrapper for planned-artifact materialization."""
    from bioetl.composition.runtime_builders._run_manifest_planned_artifacts import (
        build_planned_artifacts as impl,
    )

    return impl(
        settings=settings,
        provider=provider,
        entity=entity,
        run_id=run_id,
        pipeline_name=pipeline_name,
        workflow_id=workflow_id,
        debug_export_root=debug_export_root,
    )


def __getattr__(name: str) -> object:  # pragma: no cover
    """Lazily expose legacy path helpers without raising their static fan-in."""
    if TYPE_CHECKING:
        raise AttributeError
    if name in {"control_plane_root", "build_planned_artifacts"}:
        # Prefer explicit wrappers above; keep __getattr__ for symmetry.
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
