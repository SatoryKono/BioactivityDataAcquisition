"""Helper surfaces for composite control-plane builders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    coerce_run_id as _coerce_run_id,
)
from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_composite_effective_config_artifact,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    build_contract_identity_field_values,
    resolve_contract_identity,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    is_critical_reproducibility_runtime,
    resolve_effective_required_persistence_profile,
)

_COMPOSITE_REQUIRED_PERSISTENCE_PROFILE = "degraded_observable"

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.domain.composite import CompositeConfig

@dataclass(frozen=True, slots=True)
class CompositeControlPlaneConfigArtifacts:
    """Resolved config/contract artifacts for composite control-plane bootstrap."""

    effective_config_artifact_id: str
    resolved_config_hash: str
    effective_config_hash: str
    source_fingerprint: str
    dq_contract_compatibility_hash: str
    contract_ref: str
    contract_entity: str
    contract_version: str | None
    contract_schema_hash: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None
    normalization_profile_ref: str | None
    normalization_profile_version: str | None
    normalization_profile_hash: str | None
    pipeline_version: str
    effective_required_profile: str

__all__ = [
    "CompositeControlPlaneConfigArtifacts",
    "_build_composite_control_plane_config_artifacts",
    "_composite_manifest_contract_identity_kwargs",
    "_read_composite_control_plane_settings",
    "_resolve_composite_contract_coordinates",
    "_resolve_composite_required_persistence_profile",
]

def _composite_contract_identity_field_values(
    *,
    contract_ref: str,
    contract_version: str | None,
    contract_schema_hash: str | None,
    dq_policy_ref: str | None,
    rule_bundle_version: str | None,
    normalization_profile_ref: str | None,
    normalization_profile_version: str | None,
    normalization_profile_hash: str | None,
) -> dict[str, object]:
    """Return the shared contract-identity payload for manifest assembly."""
    return dict(
        build_contract_identity_field_values(
            contract_ref=contract_ref,
            contract_version=contract_version,
            contract_schema_hash=contract_schema_hash,
            dq_policy_ref=dq_policy_ref,
            rule_bundle_version=rule_bundle_version,
            normalization_profile_ref=normalization_profile_ref,
            normalization_profile_version=normalization_profile_version,
            normalization_profile_hash=normalization_profile_hash,
        )
    )

def _composite_manifest_contract_identity_kwargs(
    artifacts: CompositeControlPlaneConfigArtifacts,
) -> dict[str, object]:
    """Project contract-identity fields from resolved config artifacts."""
    return _composite_contract_identity_field_values(
        contract_ref=artifacts.contract_ref,
        contract_version=artifacts.contract_version,
        contract_schema_hash=artifacts.contract_schema_hash,
        dq_policy_ref=artifacts.dq_policy_ref,
        rule_bundle_version=artifacts.rule_bundle_version,
        normalization_profile_ref=artifacts.normalization_profile_ref,
        normalization_profile_version=artifacts.normalization_profile_version,
        normalization_profile_hash=artifacts.normalization_profile_hash,
    )

def _read_pipeline_control_plane(settings: object) -> object | None:
    """Return pipeline.control_plane settings for one composite launch."""
    return getattr(getattr(settings, "pipeline", None), "control_plane", None)

def _read_configured_required_persistence_profile(
    control_plane: object | None,
) -> str:
    """Return configured profile or the composite rebuild/resume default."""
    return str(
        getattr(
            control_plane,
            "required_persistence_profile",
            _COMPOSITE_REQUIRED_PERSISTENCE_PROFILE,
        )
    )

def _read_composite_control_plane_settings(
    settings: object,
) -> tuple[object | None, bool, bool, str, str]:
    """Return control-plane view and resolved persistence profile for composite runs."""
    control_plane = _read_pipeline_control_plane(settings)
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    required_profile = _read_configured_required_persistence_profile(control_plane)
    effective_required_profile = _resolve_composite_required_persistence_profile(
        settings,
        configured_required_profile=required_profile,
    )
    return (
        control_plane,
        manifest_enabled,
        ledger_enabled,
        required_profile,
        effective_required_profile,
    )

def _resolve_composite_required_persistence_profile(
    settings: object,
    *,
    configured_required_profile: object,
) -> str:
    """Resolve composite launches against the rebuild/resume default."""
    return resolve_effective_required_persistence_profile(
        configured_required_profile=configured_required_profile,
        family_default_profile=_COMPOSITE_REQUIRED_PERSISTENCE_PROFILE,
        critical_runtime=is_critical_reproducibility_runtime(
            runtime_environment=getattr(settings, "env", None),
            debug_mode=getattr(settings, "debug", False),
        ),
    )

def _build_composite_control_plane_config_artifacts(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
) -> CompositeControlPlaneConfigArtifacts:
    """Build configuration and contract artifacts for composite control plane."""
    _, _, _, _, effective_required_profile = _read_composite_control_plane_settings(
        infra_context.settings
    )
    contract_ref, contract_entity = _resolve_composite_contract_coordinates(config)
    contract_identity = resolve_contract_identity(
        provider="composite",
        entity=contract_entity,
        strict=effective_required_profile in STRICT_PERSISTENCE_PROFILES,
    )
    contract_version = contract_identity.contract_version
    contract_schema_hash = contract_identity.contract_schema_hash
    dq_policy_ref = contract_identity.dq_policy_ref
    rule_bundle_version = contract_identity.rule_bundle_version
    normalization_profile_ref = contract_identity.normalization_profile_ref
    normalization_profile_version = contract_identity.normalization_profile_version
    normalization_profile_hash = contract_identity.normalization_profile_hash
    pipeline_version = getattr(config, "version", "") or ""
    (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        source_fingerprint,
        dq_contract_compatibility_hash,
    ) = create_and_persist_composite_effective_config_artifact(
        pipeline_name=config.name,
        config=config,
        runtime_config=runtime,
        required_persistence_profile=effective_required_profile,
        normalization_profile_ref=normalization_profile_ref,
        normalization_profile_version=normalization_profile_version,
        normalization_profile_hash=normalization_profile_hash,
        settings=infra_context.settings,
        logger=infra_context.logger,
        run_id=_coerce_run_id(infra_context.run_id),
    )
    return CompositeControlPlaneConfigArtifacts(
        effective_config_artifact_id=effective_config_artifact_id,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        contract_entity=contract_entity,
        pipeline_version=pipeline_version,
        effective_required_profile=effective_required_profile,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
        normalization_profile_ref=normalization_profile_ref,
        normalization_profile_version=normalization_profile_version,
        normalization_profile_hash=normalization_profile_hash,
    )

def _resolve_composite_contract_coordinates(
    config: CompositeConfig,
) -> tuple[str, str]:
    """Resolve canonical dotted contract identity for one composite pipeline."""
    pipeline_name = str(getattr(config, "name", "") or "").strip()
    if not pipeline_name:
        raise RuntimeError("Composite config requires a non-empty name")
    entity = (
        pipeline_name.removeprefix("composite_")
        if pipeline_name.startswith("composite_")
        else pipeline_name
    )
    entity = entity.strip()
    if not entity:
        raise RuntimeError(
            f"Composite config name '{pipeline_name}' does not resolve a contract entity"
        )
    return f"composite.{entity}", entity
