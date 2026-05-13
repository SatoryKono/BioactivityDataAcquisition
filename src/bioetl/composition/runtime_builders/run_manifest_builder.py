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
    emit_replay_reconstructability_metric,
)
from bioetl.composition.runtime_builders._run_manifest_publication_support import (
    create_manifest_record,
    create_manifest_store,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    resolve_required_artifact_lineage_layers,
    validate_required_persistence_profile,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
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
    contract_ref = f"{provider}.{entity}"
    reproducibility_context = resolve_manifest_reproducibility_context(
        ctx=ctx,
        inputs=inputs,
        provider=provider,
        entity=entity,
        contract_ref=contract_ref,
    )
    contract_identity = _resolve_manifest_contract_identity(
        provider=provider,
        entity=entity,
        required_persistence_profile=(
            reproducibility_context.required_persistence_profile
        ),
        exact_replay_requested=bool(getattr(ctx, "exact_replay", False)),
    )
    _validate_manifest_persistence_requirements(
        yaml_config=yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
        ledger_enabled=ledger_enabled,
        required_profile=reproducibility_context.required_persistence_profile,
        strict_exact_replay_supported=(
            reproducibility_context.strict_exact_replay_supported
        ),
    )
    manifest_create_request = _build_manifest_create_request(
        ctx=ctx,
        inputs=inputs,
        provider=provider,
        entity=entity,
        run_type_value=run_type_value,
        execution_context_value=execution_context_value,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_identity=contract_identity,
    )
    manifest_store = create_manifest_store(inputs)
    ledger_service = _maybe_create_ledger_service(
        ledger_enabled=ledger_enabled,
        inputs=inputs,
        ctx=ctx,
    )
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
        contract_identity[0],
        contract_identity[1],
        contract_identity[2],
        contract_identity[3],
        contract_identity[4],
        contract_identity[5],
        contract_identity[6],
        contract_identity[7],
    )
    return control_plane_refs, ledger_service


def _resolve_manifest_contract_identity(
    *,
    provider: str,
    entity: str,
    required_persistence_profile: str,
    exact_replay_requested: bool,
) -> tuple[
    str,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
]:
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
    run_type_value: str,
    execution_context_value: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    contract_identity: tuple[
        str,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
    ],
) -> object:
    (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
        normalization_profile_ref,
        normalization_profile_version,
        normalization_profile_hash,
    ) = contract_identity
    return build_manifest_create_request(
        _RunManifestCreateRequestInputs(
            ctx=ctx,
            inputs=inputs,
            provider=provider,
            entity=entity,
            run_type_value=run_type_value,
            execution_context_value=execution_context_value,
            config_hash=resolved_config_hash,
            resolved_config_hash=resolved_config_hash,
            effective_config_hash=effective_config_hash,
            contract_ref=contract_ref,
            contract_version=contract_version,
            contract_schema_hash=contract_schema_hash,
            dq_policy_ref=dq_policy_ref,
            rule_bundle_version=rule_bundle_version,
            normalization_profile_ref=normalization_profile_ref,
            normalization_profile_version=normalization_profile_version,
            normalization_profile_hash=normalization_profile_hash,
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
