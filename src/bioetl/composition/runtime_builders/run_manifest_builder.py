"""Run manifest builder orchestration facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import bioetl.composition.runtime_builders.run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.composition.runtime_builders._manifest_publication_context_support import (
    ResolvedManifestPublicationContext,
    resolve_manifest_publication_identity,
    resolve_manifest_publication_context,
)
from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    ManifestReproducibilityContext,
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
from bioetl.composition.runtime_builders._runner_control_plane_policy_support import (
    validate_manifest_persistence_requirements,
)
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.service import (
        RunManifestCreateSpec,
    )
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.domain.control_plane import RunManifest
    from bioetl.domain.context import PipelineRunContext

RunManifestProvenanceBundle = _manifest_support.RunManifestProvenanceBundle


def _create_control_plane_refs(
    *,
    manifest: RunManifest,
    provenance: RunManifestProvenanceBundle,
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
        manifest_id=manifest.manifest_id,
        execution_fingerprint=manifest.execution_fingerprint,
        resolved_config_hash=provenance.resolved_config_hash,
        effective_config_hash=provenance.effective_config_hash,
        source_fingerprint=provenance.source_fingerprint,
        dq_contract_compatibility_hash=provenance.dq_contract_compatibility_hash,
        effective_config_artifact_id=provenance.effective_config_artifact_id,
        replay_parentage=(
            getattr(manifest, "replay_of_run_id", None),
            getattr(manifest, "replay_of_manifest_id", None),
        ),
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        contract=(
            contract_identity.contract_ref,
            contract_identity.contract_version,
            contract_identity.contract_schema_hash,
        ),
        policy=(
            contract_identity.dq_policy_ref,
            contract_identity.rule_bundle_version,
        ),
        normalization_profile=(
            contract_identity.normalization_profile_ref,
            contract_identity.normalization_profile_version,
            contract_identity.normalization_profile_hash,
        ),
        required_persistence_profile=required_persistence_profile,
    )


def create_run_manifest(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
    provenance: RunManifestProvenanceBundle,
    reproducibility_context: ManifestReproducibilityContext | None = None,
    contract_identity: _manifest_support.RunManifestContractIdentity | None = None,
) -> tuple[_manifest_support.ManifestControlPlaneRefs, RunLedgerService | None]:
    run_type_value, execution_context_value = (
        _manifest_support.resolve_run_context_values(ctx)
    )
    manifest_context = resolve_manifest_publication_context(
        ctx, inputs, reproducibility_context, contract_identity
    )
    validate_manifest_persistence_requirements(
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
        provenance=provenance,
        contract_identity=manifest_context.contract_identity,
    )
    return _publish_manifest_and_refs(
        ctx=ctx,
        inputs=inputs,
        ledger_enabled=ledger_enabled,
        manifest_context=manifest_context,
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
        provenance=provenance,
        contract_identity=manifest_context.contract_identity,
        required_persistence_profile=(
            manifest_context.reproducibility_context.required_persistence_profile
        ),
    )
    return control_plane_refs, ledger_service


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
    contract_identity: _manifest_support.RunManifestContractIdentity,
) -> RunManifestCreateSpec:
    reproducibility_context, contract_identity = resolve_manifest_publication_identity(
        ctx=ctx,
        inputs=inputs,
        provider=provider,
        entity=entity,
        reproducibility_context=reproducibility_context,
        contract_identity=contract_identity,
    )
    return cast(
        "RunManifestCreateSpec",
        build_manifest_create_request(
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
            )
        ),
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
