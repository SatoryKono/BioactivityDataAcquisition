"""Effective config artifact creation for control-plane."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.effective_config.service import (
    create_effective_config_service,
)
from bioetl.composition.bootstrap.control_plane_store_builders import (
    create_effective_config_artifact_store,
)
from bioetl.composition.runtime_builders._manifest_publication_context_support import (
    ensure_manifest_publication_identity,
    resolve_manifest_publication_context,
    resolve_manifest_publication_identity,
)
from bioetl.composition.runtime_builders._effective_config_artifact_builder_support import (
    build_composite_runtime_overrides_snapshot,
    build_effective_config_source_refs as build_effective_config_source_refs,
    build_resolved_config_snapshot,
    build_runtime_overrides_snapshot,
    resolve_effective_config_entity,
)
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
)

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
        RunManifestContractIdentity,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config.settings_api import Settings


def _create_and_persist_effective_config_artifact_payload(
    *,
    pipeline_name: str,
    pipeline_kind: str,
    resolved_config: object,
    runtime_overrides: dict[str, object],
    provider: str,
    entity: str,
    required_persistence_profile: str,
    resolution_policy: ConfigResolutionPolicy | None,
    normalization_profile: tuple[str | None, str | None, str | None],
    settings: Settings,
    logger: object,
    run_id: RunID,
) -> tuple[str, str, str, str, str]:
    """Persist one effective-config artifact and return its provenance anchors."""
    (
        normalization_profile_ref,
        normalization_profile_version,
        normalization_profile_hash,
    ) = normalization_profile
    service = create_effective_config_service()
    artifact = service.create_effective_config_artifact(
        pipeline_name=pipeline_name,
        pipeline_kind=pipeline_kind,
        resolved_config=build_resolved_config_snapshot(resolved_config),
        runtime_overrides=runtime_overrides,
        source_refs=build_effective_config_source_refs(
            provider=provider,
            entity=resolve_effective_config_entity(provider, entity),
        ),
        resolution_policy=resolution_policy,
        required_persistence_profile=required_persistence_profile,
        normalization_profile_ref=normalization_profile_ref,
        normalization_profile_version=normalization_profile_version,
        normalization_profile_hash=normalization_profile_hash,
    )
    serialized_payload = service.serialize_artifact(artifact)
    loaded_payload = json.loads(serialized_payload)
    if not isinstance(loaded_payload, dict):
        raise ValueError("Effective-config artifact payload must be a JSON object")
    artifact_payload = {str(key): value for key, value in loaded_payload.items()}
    artifact_store = create_effective_config_artifact_store(settings=settings)
    try:
        artifact_store.save(
            artifact_id=artifact.artifact_id,
            run_id=run_id,
            payload=artifact_payload,
        )
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        log_error = getattr(logger, "error", None)
        if callable(log_error):
            log_error(
                "effective_config_artifact_persist_failed",
                artifact_id=artifact.artifact_id,
                pipeline_name=pipeline_name,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise
    log_info = getattr(logger, "info", None)
    if callable(log_info):
        log_info(
            "effective_config_artifact_persisted",
            artifact_id=artifact.artifact_id,
            pipeline_name=pipeline_name,
            resolved_config_hash=artifact.resolved_config_hash,
            effective_config_hash=artifact.effective_config_hash,
            dq_contract_compatibility_hash=artifact.dq_contract_compatibility_hash,
        )
    return (
        artifact.artifact_id,
        artifact.resolved_config_hash,
        artifact.effective_config_hash,
        artifact.source_fingerprint,
        artifact.dq_contract_compatibility_hash,
    )


def create_and_persist_effective_config_artifact(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    reproducibility_context: object | None = None,
    contract_identity: RunManifestContractIdentity | None = None,
) -> tuple[str, str, str, str, str]:
    """Create effective config artifact, persist it, and return provenance fields."""
    manifest_context = resolve_manifest_publication_context(
        ctx, inputs, reproducibility_context, contract_identity
    )
    reproducibility_context = manifest_context.reproducibility_context
    contract_identity = manifest_context.contract_identity
    return _create_and_persist_effective_config_artifact_payload(
        pipeline_name=ctx.pipeline_name,
        pipeline_kind="standard",
        resolved_config=inputs.yaml_config,
        runtime_overrides=build_runtime_overrides_snapshot(ctx, inputs.settings),
        provider=provider,
        entity=entity,
        required_persistence_profile=(
            reproducibility_context.required_persistence_profile
        ),
        resolution_policy=ConfigResolutionPolicy(
            strict_validation=bool(
                getattr(
                    inputs.runtime_config,
                    "strict_gold_validation",
                    getattr(inputs.runtime_config, "strict_validation", False),
                )
            )
        ),
        normalization_profile=(
            contract_identity.normalization_profile_ref,
            contract_identity.normalization_profile_version,
            contract_identity.normalization_profile_hash,
        ),
        settings=inputs.settings,
        logger=inputs.observability.logger,
        run_id=ctx.run_id,
    )


def create_and_persist_composite_effective_config_artifact(
    *,
    pipeline_name: str,
    config: object,
    runtime_config: object,
    required_persistence_profile: str,
    normalization_profile_ref: str | None,
    normalization_profile_version: str | None,
    normalization_profile_hash: str | None,
    settings: Settings,
    logger: object,
    run_id: RunID,
) -> tuple[str, str, str, str, str]:
    """Persist the composite effective-config artifact using the shared path."""
    return _create_and_persist_effective_config_artifact_payload(
        pipeline_name=pipeline_name,
        pipeline_kind="composite",
        resolved_config=config,
        runtime_overrides=build_composite_runtime_overrides_snapshot(
            pipeline_name=pipeline_name,
            runtime_config=runtime_config,
            required_persistence_profile=required_persistence_profile,
            settings=settings,
        ),
        provider="composite",
        entity=pipeline_name,
        required_persistence_profile=required_persistence_profile,
        resolution_policy=ConfigResolutionPolicy(
            strict_validation=bool(
                getattr(
                    runtime_config,
                    "strict_gold_validation",
                    getattr(runtime_config, "strict_validation", False),
                )
            )
        ),
        normalization_profile=(
            normalization_profile_ref,
            normalization_profile_version,
            normalization_profile_hash,
        ),
        settings=settings,
        logger=logger,
        run_id=run_id,
    )


__all__ = [
    "create_and_persist_composite_effective_config_artifact",
    "create_and_persist_effective_config_artifact",
    "ensure_manifest_publication_identity",
    "resolve_manifest_publication_context",
    "resolve_manifest_publication_identity",
]
