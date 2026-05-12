"""Helper surfaces for composite control-plane builders."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    coerce_run_id as _coerce_run_id,
)
from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_composite_effective_config_artifact,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    resolve_contract_identity,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    is_critical_reproducibility_runtime,
    resolve_effective_required_persistence_profile,
)

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.domain.composite.config import CompositeConfig

__all__ = [
    "_build_composite_control_plane_config_artifacts",
    "_resolve_composite_contract_coordinates",
    "_resolve_composite_required_persistence_profile",
]


def _resolve_composite_required_persistence_profile(
    settings: object,
    *,
    configured_required_profile: object,
) -> str:
    """Resolve composite launches against the published replay-ready default."""
    return resolve_effective_required_persistence_profile(
        configured_required_profile=configured_required_profile,
        family_default_profile="replay_ready",
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
) -> tuple[
    str,
    str,
    str,
    str,
    str,
    str | None,
    str | None,
    str | None,
    str | None,
    str,
    str,
]:
    """Build configuration and contract artifacts for composite control plane."""
    control_plane = getattr(
        getattr(infra_context.settings, "pipeline", None), "control_plane", None
    )
    required_profile = getattr(
        control_plane,
        "required_persistence_profile",
        "degraded_observable",
    )
    effective_required_profile = _resolve_composite_required_persistence_profile(
        infra_context.settings,
        configured_required_profile=required_profile,
    )
    contract_ref, contract_entity = _resolve_composite_contract_coordinates(config)
    (
        _resolved_contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    ) = resolve_contract_identity(
        provider="composite",
        entity=contract_entity,
        strict=effective_required_profile in STRICT_PERSISTENCE_PROFILES,
    )
    pipeline_version = getattr(config, "version", "") or ""
    (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        dq_contract_compatibility_hash,
    ) = create_and_persist_composite_effective_config_artifact(
        pipeline_name=config.name,
        config=config,
        runtime_config=runtime,
        required_persistence_profile=effective_required_profile,
        settings=infra_context.settings,
        logger=infra_context.logger,
        run_id=_coerce_run_id(infra_context.run_id),
    )
    return (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        dq_contract_compatibility_hash,
        contract_ref,
        contract_entity,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
        pipeline_version,
        effective_required_profile,
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
