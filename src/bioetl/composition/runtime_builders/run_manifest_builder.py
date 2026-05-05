"""Run manifest builder orchestration facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

import bioetl.composition.runtime_builders._run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    resolve_manifest_reproducibility_context,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support import (
    _RunManifestCreateRequestInputs,
    build_manifest_create_request,
    create_ledger_service,
    create_manifest_record,
    create_manifest_store,
    emit_replay_reconstructability_metric,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    resolve_required_artifact_lineage_layers,
    validate_required_persistence_profile,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    legacy_config_hash_from_resolved_config_hash,
)

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


def create_run_manifest(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
    effective_config_artifact_id: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
) -> tuple[_manifest_support.ManifestControlPlaneRefs, RunLedgerService | None]:
    yaml_config = inputs.yaml_config
    run_type_value, execution_context_value = (
        _manifest_support.resolve_run_context_values(ctx)
    )
    provider, entity = _manifest_support.resolve_provider_entity(
        pipeline_name=ctx.pipeline_name,
        yaml_config=yaml_config,
    )
    (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    ) = _manifest_support.resolve_contract_identity(provider=provider, entity=entity)
    reproducibility_context = resolve_manifest_reproducibility_context(
        ctx=ctx,
        inputs=inputs,
        provider=provider,
        entity=entity,
        contract_ref=contract_ref,
    )
    _active_layers, missing_artifact_lineage_layers = (
        resolve_required_artifact_lineage_layers(
            yaml_config=yaml_config,
            skip_gold=bool(getattr(ctx, "skip_gold", False)),
        )
    )
    manifest_create_request = build_manifest_create_request(
        _RunManifestCreateRequestInputs(
            ctx=ctx,
            inputs=inputs,
            provider=provider,
            entity=entity,
            run_type_value=run_type_value,
            execution_context_value=execution_context_value,
            config_hash=legacy_config_hash_from_resolved_config_hash(
                resolved_config_hash
            ),
            resolved_config_hash=resolved_config_hash,
            effective_config_hash=effective_config_hash,
            contract_ref=contract_ref,
            contract_version=contract_version,
            contract_schema_hash=contract_schema_hash,
            dq_policy_ref=dq_policy_ref,
            rule_bundle_version=rule_bundle_version,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
        )
    )
    validate_required_persistence_profile(
        manifest_enabled=True,
        ledger_enabled=ledger_enabled,
        required_profile=reproducibility_context.required_persistence_profile,
        execution_label="Pipeline execution",
        exact_replay_execution_context_supported=(
            reproducibility_context.strict_exact_replay_supported
        ),
        missing_artifact_lineage_layers=missing_artifact_lineage_layers,
    )
    manifest_store = create_manifest_store(inputs)
    ledger_service: RunLedgerService | None = None
    if ledger_enabled:
        ledger_service = create_ledger_service(inputs, ctx)
    emit_replay_reconstructability_metric(
        request=manifest_create_request,
        strict_exact_replay_supported=(
            reproducibility_context.strict_exact_replay_supported
        ),
        metrics=inputs.observability.metrics,
    )
    manifest = create_manifest_record(
        manifest_store=manifest_store,
        manifest_create_request=manifest_create_request,
        ledger_service=ledger_service,
    )
    control_plane_refs = _manifest_support.create_control_plane_refs(
        manifest.manifest_id,
        manifest.execution_fingerprint,
        resolved_config_hash,
        effective_config_hash,
        dq_contract_compatibility_hash,
        effective_config_artifact_id,
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    )
    return control_plane_refs, ledger_service
