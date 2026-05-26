"""Run manifest builder orchestration facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import bioetl.composition.runtime_builders.run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    resolve_manifest_reproducibility_context,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support import (
    _RunManifestCreateRequestInputs,
    build_manifest_create_request,
    create_ledger_service,
    emit_replay_reconstructability_metric,
)
from bioetl.composition.runtime_builders._run_manifest_publication_support import (
    create_manifest_record,
    create_manifest_store,
)
from bioetl.composition.runtime_builders._runner_control_plane_policy import (
    resolve_required_artifact_lineage_layers,
    validate_required_persistence_profile,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


@dataclass(frozen=True, slots=True)
class _ResolvedManifestContext:
    provider: str
    entity: str
    contract_identity: _manifest_support.RunManifestContractIdentity
    reproducibility_context: object


def _resolve_manifest_context(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    reproducibility_context: object | None = None,
    contract_identity: _manifest_support.RunManifestContractIdentity | None = None,
) -> _ResolvedManifestContext:
    """Resolve manifest family, contract identity, and reproducibility context."""
    provider, entity = _manifest_support.resolve_provider_entity(
        pipeline_name=ctx.pipeline_name,
        yaml_config=inputs.yaml_config,
    )
    contract_ref = f"{provider}.{entity}"
    if reproducibility_context is None:
        reproducibility_context = resolve_manifest_reproducibility_context(
            ctx=ctx,
            inputs=inputs,
            provider=provider,
            entity=entity,
            contract_ref=contract_ref,
        )
    return _ResolvedManifestContext(
        provider=provider,
        entity=entity,
        contract_identity=contract_identity
        or _resolve_manifest_contract_identity(
            provider=provider,
            entity=entity,
            required_persistence_profile=(
                reproducibility_context.required_persistence_profile
            ),
            exact_replay_requested=bool(getattr(ctx, "exact_replay", False)),
        ),
        reproducibility_context=reproducibility_context,
    )


def _create_control_plane_refs(
    *,
    manifest: object,
    resolved_config_hash: str,
    effective_config_hash: str,
    source_fingerprint: str | None,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    contract_identity: _manifest_support.RunManifestContractIdentity,
    required_persistence_profile: str,
) -> _manifest_support.ManifestControlPlaneRefs:
    """Build canonical control-plane refs from one persisted manifest record."""
    input_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
        [
            snapshot
            for source_ref in getattr(manifest, "source_refs", ())
            for snapshot in getattr(source_ref, "input_snapshots", ())
        ]
    )
    return _manifest_support.create_control_plane_refs(
        manifest.manifest_id,
        manifest.execution_fingerprint,
        resolved_config_hash,
        effective_config_hash,
        source_fingerprint,
        dq_contract_compatibility_hash,
        effective_config_artifact_id,
        getattr(manifest, "replay_of_run_id", None),
        getattr(manifest, "replay_of_manifest_id", None),
        input_snapshot_fingerprint,
        contract_identity.contract_ref,
        contract_identity.contract_version,
        contract_identity.contract_schema_hash,
        contract_identity.dq_policy_ref,
        contract_identity.rule_bundle_version,
        contract_identity.normalization_profile_ref,
        contract_identity.normalization_profile_version,
        contract_identity.normalization_profile_hash,
        required_persistence_profile,
    )


def create_run_manifest(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
    effective_config_artifact_id: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    source_fingerprint: str | None,
    dq_contract_compatibility_hash: str,
    reproducibility_context: object | None = None,
    contract_identity: _manifest_support.RunManifestContractIdentity | None = None,
) -> tuple[_manifest_support.ManifestControlPlaneRefs, RunLedgerService | None]:
    run_type_value, execution_context_value = (
        _manifest_support.resolve_run_context_values(ctx)
    )
    manifest_context = _resolve_manifest_context(
        ctx=ctx,
        inputs=inputs,
        reproducibility_context=reproducibility_context,
        contract_identity=contract_identity,
    )
    _validate_manifest_persistence_requirements(
        yaml_config=inputs.yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
        ledger_enabled=ledger_enabled,
        required_profile=manifest_context.reproducibility_context.required_persistence_profile,
        strict_exact_replay_supported=(
            manifest_context.reproducibility_context.strict_exact_replay_supported
        ),
    )
    manifest_create_request = _build_manifest_create_request(
        ctx=ctx,
        inputs=inputs,
        provider=manifest_context.provider,
        entity=manifest_context.entity,
        reproducibility_context=manifest_context.reproducibility_context,
        run_type_value=run_type_value,
        execution_context_value=execution_context_value,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_identity=manifest_context.contract_identity,
    )
    return _publish_manifest_and_refs(
        ctx=ctx,
        inputs=inputs,
        ledger_enabled=ledger_enabled,
        manifest_context=manifest_context,
        manifest_create_request=manifest_create_request,
        effective_config_artifact_id=effective_config_artifact_id,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
    )


def _publish_manifest_and_refs(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
    manifest_context: _ResolvedManifestContext,
    manifest_create_request: object,
    effective_config_artifact_id: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    source_fingerprint: str | None,
    dq_contract_compatibility_hash: str,
) -> tuple[_manifest_support.ManifestControlPlaneRefs, RunLedgerService | None]:
    """Persist the manifest record and translate it into runner control-plane refs."""
    manifest_store = create_manifest_store(inputs)
    ledger_service = _maybe_create_ledger_service(
        ledger_enabled=ledger_enabled,
        inputs=inputs,
        ctx=ctx,
    )
    emit_replay_reconstructability_metric(
        request=manifest_create_request,
        strict_exact_replay_supported=(
            manifest_context.reproducibility_context.strict_exact_replay_supported
        ),
        metrics=inputs.observability.metrics,
    )
    manifest = create_manifest_record(
        manifest_store=manifest_store,
        manifest_create_request=manifest_create_request,
        ledger_service=ledger_service,
    )
    control_plane_refs = _create_control_plane_refs(
        manifest=manifest,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_identity=manifest_context.contract_identity,
        required_persistence_profile=(
            manifest_context.reproducibility_context.required_persistence_profile
        ),
    )
    return control_plane_refs, ledger_service


def _resolve_manifest_contract_identity(
    *,
    provider: str,
    entity: str,
    required_persistence_profile: str,
    exact_replay_requested: bool,
) -> _manifest_support.RunManifestContractIdentity:
    return _manifest_support.resolve_contract_identity(
        provider=provider,
        entity=entity,
        strict=exact_replay_requested
        or required_persistence_profile in STRICT_PERSISTENCE_PROFILES,
    )


def _validate_manifest_persistence_requirements(
    *,
    yaml_config: object,
    skip_gold: bool,
    ledger_enabled: bool,
    required_profile: str,
    strict_exact_replay_supported: bool,
) -> None:
    _active_layers, missing_artifact_lineage_layers = (
        resolve_required_artifact_lineage_layers(
            yaml_config=yaml_config,
            skip_gold=skip_gold,
        )
    )
    validate_required_persistence_profile(
        manifest_enabled=True,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        execution_label="Pipeline execution",
        exact_replay_execution_context_supported=strict_exact_replay_supported,
        composite_resume_rich_replay_supported=True,
        missing_artifact_lineage_layers=missing_artifact_lineage_layers,
    )


def _build_manifest_create_request(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    reproducibility_context: object,
    run_type_value: str,
    execution_context_value: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    source_fingerprint: str | None,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    contract_identity: _manifest_support.RunManifestContractIdentity,
) -> object:
    return build_manifest_create_request(
        _RunManifestCreateRequestInputs(
            ctx=ctx,
            inputs=inputs,
            provider=provider,
            entity=entity,
            reproducibility_context=reproducibility_context,
            run_type_value=run_type_value,
            execution_context_value=execution_context_value,
            config_hash=_manifest_support.legacy_config_hash_from_resolved_config_hash(
                resolved_config_hash
            ),
            resolved_config_hash=resolved_config_hash,
            effective_config_hash=effective_config_hash,
            source_fingerprint=source_fingerprint,
            contract_ref=contract_identity.contract_ref,
            contract_version=contract_identity.contract_version,
            contract_schema_hash=contract_identity.contract_schema_hash,
            dq_policy_ref=contract_identity.dq_policy_ref,
            rule_bundle_version=contract_identity.rule_bundle_version,
            normalization_profile_ref=contract_identity.normalization_profile_ref,
            normalization_profile_version=contract_identity.normalization_profile_version,
            normalization_profile_hash=contract_identity.normalization_profile_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
        )
    )


def _maybe_create_ledger_service(
    *,
    ledger_enabled: bool,
    inputs: RunnerInputs,
    ctx: PipelineRunContext,
) -> RunLedgerService | None:
    if not ledger_enabled:
        return None
    return create_ledger_service(inputs, ctx)
