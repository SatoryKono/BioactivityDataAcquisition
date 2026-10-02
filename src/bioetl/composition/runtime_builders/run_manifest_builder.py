"""Run manifest builder orchestration facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.ledger.service import RunLedgerService
from bioetl.composition.runtime_builders.run_manifest_support import (
    ManifestControlPlaneRefs,
    RunManifestContractIdentity,
    RunManifestProvenanceBundle,
    build_run_manifest_provenance_bundle as build_run_manifest_provenance_bundle,
    resolve_run_context_values,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    create_control_plane_refs_for_manifest,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support import (
    build_manifest_create_request,
    create_ledger_service,
    emit_replay_reconstructability_metric,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
    RunManifestCreateRequestInputs,
)
from bioetl.composition.runtime_builders._run_manifest_publication_support import (
    create_manifest_record,
    create_manifest_store,
)
from bioetl.composition.runtime_builders.input_snapshot_resolution import (
    resolve_cached_bronze_input_snapshot_refs,
    resolve_pipeline_input_snapshot_refs as resolve_pipeline_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._runner_control_plane_policy import (
    validate_manifest_persistence_requirements,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.service import (
        RunManifestCreateSpec,
    )
    from bioetl.composition.runtime_builders._manifest_publication_context_support import (
        ResolvedManifestPublicationContext,
    )
    from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
        ManifestReproducibilityContext,
    )
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.domain.context import PipelineRunContext


def create_run_manifest(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
    provenance: RunManifestProvenanceBundle,
    publication_context: ResolvedManifestPublicationContext,
) -> tuple[ManifestControlPlaneRefs, RunLedgerService | None]:
    run_type_value, execution_context_value = resolve_run_context_values(ctx)
    validate_manifest_persistence_requirements(
        yaml_config=inputs.yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
        ledger_enabled=ledger_enabled,
        required_profile=publication_context.reproducibility_context.required_persistence_profile,
        strict_exact_replay_supported=(
            publication_context.reproducibility_context.strict_exact_replay_supported
        ),
    )
    manifest_create_request = _build_manifest_create_request(
        ctx=ctx,
        inputs=inputs,
        provider=publication_context.provider,
        entity=publication_context.entity,
        reproducibility_context=publication_context.reproducibility_context,
        run_type_value=run_type_value,
        execution_context_value=execution_context_value,
        provenance=provenance,
        contract_identity=publication_context.contract_identity,
        ledger_enabled=ledger_enabled,
    )
    return _publish_manifest_and_refs(
        ctx=ctx,
        inputs=inputs,
        ledger_enabled=ledger_enabled,
        manifest_context=publication_context,
        manifest_create_request=manifest_create_request,
        provenance=provenance,
    )


def _publish_manifest_and_refs(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
    manifest_context: ResolvedManifestPublicationContext,
    manifest_create_request: RunManifestCreateSpec,
    provenance: RunManifestProvenanceBundle,
) -> tuple[ManifestControlPlaneRefs, RunLedgerService | None]:
    """Persist the manifest record and translate it into runner control-plane refs."""
    manifest_store = create_manifest_store(inputs)
    ledger_service = _maybe_create_ledger_service(
        ledger_enabled=ledger_enabled,
        inputs=inputs,
        ctx=ctx,
    )
    if ledger_service is not None:
        ledger_service.manifest_port = manifest_store
    emit_replay_reconstructability_metric(
        request=manifest_create_request,
        strict_exact_replay_supported=(
            manifest_context.reproducibility_context.strict_exact_replay_supported
        ),
        metrics=inputs.observability.metrics,
    )
    require_before_persist = _strict_cached_bronze_require(
        ctx=ctx,
        required_persistence_profile=(
            manifest_context.reproducibility_context.required_persistence_profile
        ),
    )
    if require_before_persist:
        _require_cached_bronze_snapshots(
            inputs=inputs, manifest_context=manifest_context
        )
    manifest = create_manifest_record(
        manifest_store=manifest_store,
        manifest_create_request=manifest_create_request,
        ledger_service=ledger_service,
    )
    if not require_before_persist:
        _require_cached_bronze_snapshots(
            inputs=inputs, manifest_context=manifest_context
        )
    control_plane_refs = create_control_plane_refs_for_manifest(
        manifest=manifest,
        provenance=provenance,
        contract_identity=manifest_context.contract_identity,
        required_persistence_profile=(
            manifest_context.reproducibility_context.required_persistence_profile
        ),
    )
    return control_plane_refs, ledger_service


def _strict_cached_bronze_require(
    *,
    ctx: PipelineRunContext,
    required_persistence_profile: str,
) -> bool:
    return bool(getattr(ctx, "exact_replay", False)) or (
        required_persistence_profile in STRICT_PERSISTENCE_PROFILES
    )


def _require_cached_bronze_snapshots(
    *,
    inputs: RunnerInputs,
    manifest_context: ResolvedManifestPublicationContext,
) -> None:
    resolve_cached_bronze_input_snapshot_refs(
        cached_bronze=inputs.cached_bronze,
        settings=inputs.settings,
        provider=manifest_context.provider,
        entity=manifest_context.entity,
        require=True,
    )


def _build_manifest_create_request(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    reproducibility_context: ManifestReproducibilityContext,
    run_type_value: str,
    execution_context_value: str,
    provenance: RunManifestProvenanceBundle,
    contract_identity: RunManifestContractIdentity,
    ledger_enabled: bool = True,
) -> RunManifestCreateSpec:
    request: RunManifestCreateSpec = build_manifest_create_request(
        RunManifestCreateRequestInputs(
            ctx=ctx,
            inputs=inputs,
            provider=provider,
            entity=entity,
            reproducibility_context=reproducibility_context,
            run_type_value=run_type_value,
            execution_context_value=execution_context_value,
            config_hash=provenance.resolved_config_hash,
            resolved_config_hash=provenance.resolved_config_hash,
            effective_config_hash=provenance.effective_config_hash,
            source_fingerprint=provenance.source_fingerprint,
            contract_identity=contract_identity,
            dq_contract_compatibility_hash=provenance.dq_contract_compatibility_hash,
            effective_config_artifact_id=provenance.effective_config_artifact_id,
            ledger_enabled=ledger_enabled,
        )
    )
    return request


def _maybe_create_ledger_service(
    *,
    ledger_enabled: bool,
    inputs: RunnerInputs,
    ctx: PipelineRunContext,
) -> RunLedgerService | None:
    if not ledger_enabled:
        return None
    return create_ledger_service(inputs, ctx)
