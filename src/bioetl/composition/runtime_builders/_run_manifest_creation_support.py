"""Private helpers for run-manifest creation orchestration."""

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
from bioetl.composition.runtime_builders import (
    _run_manifest_support as _manifest_support,
)
from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    resolve_code_revision_for_manifest,
    resolve_manifest_reproducibility_context,
    validate_required_runtime_persistence_profile,
)
from bioetl.composition.services.versioning import get_pipeline_version
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import RunnerInputs
    from bioetl.domain.context import PipelineRunContext


@dataclass(frozen=True, slots=True)
class _RunManifestCreateRequestInputs:
    ctx: PipelineRunContext
    inputs: RunnerInputs
    provider: str
    entity: str
    run_type_value: str
    execution_context_value: str
    config_hash: str
    resolved_config_hash: str
    effective_config_hash: str
    contract_ref: str
    contract_version: str | None
    contract_schema_hash: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None
    dq_contract_compatibility_hash: str
    effective_config_artifact_id: str


def create_ledger_service(
    inputs: RunnerInputs,
    ctx: PipelineRunContext,
) -> RunLedgerService | None:
    """Build the optional run-ledger service for manifest publication."""
    from bioetl.infrastructure.control_plane import FileRunLedgerStore

    return RunLedgerService(
        ledger_port=FileRunLedgerStore(
            base_path=_manifest_support.control_plane_root(
                inputs.settings, "run_ledger"
            ),
            metrics=inputs.observability.metrics,
        ),
        manifest_id="pending",
        run_id=ctx.run_id,
    )


def build_manifest_create_request(
    request_inputs: _RunManifestCreateRequestInputs,
) -> RunManifestCreateSpec:
    """Build the canonical RunManifest create request."""
    ctx = request_inputs.ctx
    inputs = request_inputs.inputs
    provider = request_inputs.provider
    entity = request_inputs.entity
    yaml_config = inputs.yaml_config
    reproducibility_context = resolve_manifest_reproducibility_context(
        ctx=ctx,
        inputs=inputs,
        provider=provider,
        entity=entity,
        contract_ref=request_inputs.contract_ref,
    )
    source_refs = _manifest_support.build_run_source_refs(
        ctx=ctx,
        cached_bronze=inputs.cached_bronze,
        settings=inputs.settings,
        provider=provider,
        entity=entity,
        required_persistence_profile=(
            reproducibility_context.required_persistence_profile
        ),
    )
    replay_of_run_id, replay_of_manifest_id = (
        _manifest_support.resolve_replay_parentage(
            ctx=ctx,
            runtime_config=inputs.runtime_config,
        )
    )
    code_revision = resolve_code_revision_for_manifest(
        resolved_config_hash=request_inputs.resolved_config_hash,
        test_mode=bool(getattr(inputs.settings, "test_mode", False)),
    )
    request = RunManifestCreateSpec(
        run_id=ctx.run_id,
        run_type=getattr(ctx, "run_type", "incremental"),
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
        launch_context=_manifest_support.build_launch_context_snapshot(
            ctx,
            run_type_value=request_inputs.run_type_value,
            execution_context_value=request_inputs.execution_context_value,
            required_persistence_profile=(
                reproducibility_context.required_persistence_profile
            ),
        ),
        runtime_config=_manifest_support.to_serializable_mapping(inputs.runtime_config),
        resolved_config=_manifest_support.to_serializable_mapping(yaml_config),
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        source_refs=source_refs,
        planned_artifacts=_manifest_support.build_planned_artifacts(
            settings=inputs.settings,
            provider=provider,
            entity=entity,
        ),
        pipeline_version=get_pipeline_version(yaml_config),
        git_commit=code_revision.git_commit,
        source_revision_state=code_revision.source_revision_state,
        dependency_lock_hash=code_revision.dependency_lock_hash,
        config_hash=request_inputs.config_hash,
        resolved_config_hash=request_inputs.resolved_config_hash,
        effective_config_hash=request_inputs.effective_config_hash,
        contract_ref=request_inputs.contract_ref,
        contract_version=request_inputs.contract_version,
        contract_schema_hash=request_inputs.contract_schema_hash,
        dq_policy_ref=request_inputs.dq_policy_ref,
        rule_bundle_version=request_inputs.rule_bundle_version,
        dq_contract_compatibility_hash=request_inputs.dq_contract_compatibility_hash,
        effective_config_artifact_id=request_inputs.effective_config_artifact_id,
        replay_capability=_manifest_support.resolve_replay_capability(
            source_refs=source_refs,
            resume_requested=bool(getattr(ctx, "resume", False)),
        ),
    )
    validate_required_runtime_persistence_profile(
        request=request,
        required_persistence_profile=(
            reproducibility_context.required_persistence_profile
        ),
        strict_exact_replay_supported=(
            reproducibility_context.strict_exact_replay_supported
        ),
    )
    return request


def emit_replay_reconstructability_metric(
    *,
    request: RunManifestCreateSpec,
    strict_exact_replay_supported: bool,
    metrics: object,
) -> None:
    """Emit replay reconstructability metrics for one manifest request."""
    increment_counter = getattr(metrics, "increment_counter", None)
    if not callable(increment_counter):
        return
    set_gauge = getattr(metrics, "set_gauge", None)
    strict_replay_requested = bool(request.launch_context.get("exact_replay"))
    required_persistence_profile = str(
        request.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    )
    strict_requirement = (
        strict_replay_requested
        or required_persistence_profile in STRICT_PERSISTENCE_PROFILES
    )
    status = "reconstructable"
    if strict_requirement and (
        not strict_exact_replay_supported
        or request.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        status = "not_reconstructable"
    raw_run_type = getattr(request.run_type, "value", request.run_type)
    run_type = str(raw_run_type or "unknown").strip().lower().replace(" ", "_")
    bounded_run_type = run_type or "unknown"
    increment_counter(
        "bioetl_replay_reconstructability_events_total",
        value=1,
        labels={
            "pipeline": request.pipeline_name,
            "replay_capability": request.replay_capability.value,
            "strict_requirement": "true" if strict_requirement else "false",
            "status": status,
        },
    )
    lag_status = "not_requested"
    if status == "not_reconstructable":
        lag_status = "blocked"
    elif strict_replay_requested:
        lag_status = "ready"
    replay_labels = {
        "pipeline": request.pipeline_name,
        "run_type": bounded_run_type,
        "replay_capability": request.replay_capability.value,
    }
    if callable(set_gauge):
        set_gauge(
            "bioetl_replay_lag_seconds",
            value=0.0,
            labels={**replay_labels, "status": lag_status},
        )
    if status == "not_reconstructable":
        increment_counter(
            "bioetl_replay_drift_events_total",
            value=1,
            labels={
                **replay_labels,
                "drift_type": "strict_replay_not_reconstructable",
                "status": "detected",
            },
        )


def create_manifest_store(inputs: RunnerInputs) -> FileRunManifestStore:
    """Create the file-backed run-manifest store."""
    return FileRunManifestStore(
        base_path=_manifest_support.control_plane_root(inputs.settings, "run_manifest"),
        metrics=inputs.observability.metrics,
    )


def create_manifest_record(
    *,
    manifest_store: FileRunManifestStore,
    manifest_create_request: RunManifestCreateSpec,
    ledger_service: RunLedgerService | None,
) -> RunManifest:
    """Create and optionally ledger-record one manifest."""
    manifest = RunManifestService(
        manifest_port=manifest_store,
        clock=SystemClock(),
    ).create_manifest(manifest_create_request)
    if ledger_service is not None:
        ledger_service.manifest_id = manifest.manifest_id
        ledger_service.record_manifest_created(manifest)
    return manifest
