"""Run manifest builder facade and orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec,
    RunManifestService,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    ManifestControlPlaneRefs as _ManifestControlPlaneRefs,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    build_launch_context_snapshot as _build_launch_context_snapshot,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    build_planned_artifacts as _build_planned_artifacts,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    build_run_source_refs as _build_run_source_refs,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    control_plane_root as _control_plane_root,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    create_control_plane_refs as _create_control_plane_refs,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_contract_identity as _resolve_contract_identity,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_provider_entity as _resolve_provider_entity,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_replay_capability as _resolve_replay_capability,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_replay_parentage as _resolve_replay_parentage,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_run_context_values as _resolve_run_context_values,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    to_serializable_mapping as _to_serializable_mapping,
)
from bioetl.composition.services.versioning import (
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.infrastructure.control_plane import FileRunManifestStore

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


@dataclass(frozen=True, slots=True)
class _RunManifestCreateRequestInputs:
    ctx: PipelineRunContext
    inputs: RunnerInputs
    provider: str
    entity: str
    run_type_value: str
    execution_context_value: str
    effective_config_hash: str
    contract_ref: str
    contract_version: str | None
    contract_schema_hash: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None
    dq_contract_compatibility_hash: str
    effective_config_artifact_id: str


def _create_ledger_service(
    inputs: RunnerInputs,
    ctx: PipelineRunContext,
) -> RunLedgerService | None:
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.infrastructure.control_plane import FileRunLedgerStore

    return RunLedgerService(
        ledger_port=FileRunLedgerStore(
            base_path=_control_plane_root(inputs.settings, "run_ledger"),
            metrics=inputs.observability.metrics,
        ),
        manifest_id="pending",
        run_id=ctx.run_id,
    )


def _build_manifest_create_request(
    request_inputs: _RunManifestCreateRequestInputs,
) -> RunManifestCreateSpec:
    ctx = request_inputs.ctx
    inputs = request_inputs.inputs
    provider = request_inputs.provider
    entity = request_inputs.entity
    yaml_config = inputs.yaml_config
    source_refs = _build_run_source_refs(
        ctx=ctx,
        cached_bronze=inputs.cached_bronze,
        settings=inputs.settings,
        provider=provider,
        entity=entity,
    )
    replay_of_run_id, replay_of_manifest_id = _resolve_replay_parentage(
        ctx=ctx,
        runtime_config=inputs.runtime_config,
    )
    control_plane = getattr(
        getattr(inputs.settings, "pipeline", None), "control_plane", None
    )
    required_persistence_profile = str(
        getattr(
            control_plane,
            "required_persistence_profile",
            "degraded_observable",
        )
    )
    request = RunManifestCreateSpec(
        run_id=ctx.run_id,
        run_type=getattr(ctx, "run_type", "incremental"),
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
        launch_context=_build_launch_context_snapshot(
            ctx,
            run_type_value=request_inputs.run_type_value,
            execution_context_value=request_inputs.execution_context_value,
            required_persistence_profile=required_persistence_profile,
        ),
        runtime_config=_to_serializable_mapping(inputs.runtime_config),
        resolved_config=_to_serializable_mapping(yaml_config),
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        source_refs=source_refs,
        planned_artifacts=_build_planned_artifacts(
            settings=inputs.settings,
            provider=provider,
            entity=entity,
        ),
        pipeline_version=get_pipeline_version(yaml_config),
        git_commit=get_git_commit(),
        config_hash=request_inputs.effective_config_hash,
        contract_ref=request_inputs.contract_ref,
        contract_version=request_inputs.contract_version,
        contract_schema_hash=request_inputs.contract_schema_hash,
        dq_policy_ref=request_inputs.dq_policy_ref,
        rule_bundle_version=request_inputs.rule_bundle_version,
        dq_contract_compatibility_hash=request_inputs.dq_contract_compatibility_hash,
        effective_config_artifact_id=request_inputs.effective_config_artifact_id,
        replay_capability=_resolve_replay_capability(
            source_refs=source_refs,
            resume_requested=bool(getattr(ctx, "resume", False)),
        ),
    )
    _validate_required_runtime_persistence_profile(
        request=request,
        required_persistence_profile=required_persistence_profile,
    )
    return request


def _validate_required_runtime_persistence_profile(
    *,
    request: RunManifestCreateSpec,
    required_persistence_profile: str,
) -> None:
    if required_persistence_profile not in {"replay_ready", "forensic_grade"}:
        return
    if request.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED:
        raise RuntimeError(
            "Pipeline execution cannot satisfy required persistence profile "
            f"'{required_persistence_profile}' because immutable input snapshots "
            "and exact replay capability are not available for this run"
        )


def create_run_manifest(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
    effective_config_artifact_id: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
) -> tuple[_ManifestControlPlaneRefs, RunLedgerService | None]:
    yaml_config = inputs.yaml_config
    run_type_value, execution_context_value = _resolve_run_context_values(ctx)
    provider, entity = _resolve_provider_entity(
        pipeline_name=ctx.pipeline_name,
        yaml_config=yaml_config,
    )
    (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    ) = _resolve_contract_identity(provider=provider, entity=entity)
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(inputs.settings, "run_manifest"),
        metrics=inputs.observability.metrics,
    )
    ledger_service: RunLedgerService | None = None
    if ledger_enabled:
        ledger_service = _create_ledger_service(inputs, ctx)
    manifest_create_request = _build_manifest_create_request(
        _RunManifestCreateRequestInputs(
            ctx=ctx,
            inputs=inputs,
            provider=provider,
            entity=entity,
            run_type_value=run_type_value,
            execution_context_value=execution_context_value,
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

    manifest = RunManifestService(manifest_port=manifest_store).create_manifest(
        manifest_create_request
    )
    if ledger_service is not None:
        ledger_service.manifest_id = manifest.manifest_id
        ledger_service.record_manifest_created(manifest)
    control_plane_refs = _create_control_plane_refs(
        manifest.manifest_id,
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
