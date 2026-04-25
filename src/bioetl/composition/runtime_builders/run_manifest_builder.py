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
    build_launch_context_snapshot as _build_launch_context_snapshot,
    build_planned_artifacts as _build_planned_artifacts,
    build_run_source_refs as _build_run_source_refs,
    control_plane_root as _control_plane_root,
    create_control_plane_refs as _create_control_plane_refs,
    resolve_contract_identity as _resolve_contract_identity,
    resolve_provider_entity as _resolve_provider_entity,
    resolve_replay_capability as _resolve_replay_capability,
    resolve_replay_parentage as _resolve_replay_parentage,
    resolve_run_context_values as _resolve_run_context_values,
    to_serializable_mapping as _to_serializable_mapping,
)
from bioetl.composition.services.versioning import (
    CodeRevisionProvenance,
    get_code_revision_provenance,
    get_pipeline_version,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_profiles import (
    resolve_reproducibility_family_profile,
)
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.time import SystemClock

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
    resolved_config_hash: str
    effective_config_hash: str
    contract_ref: str
    contract_version: str | None
    contract_schema_hash: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None
    dq_contract_compatibility_hash: str
    effective_config_artifact_id: str


_STRICT_PERSISTENCE_PROFILES = {"replay_ready", "forensic_grade"}
_REPRODUCIBLE_APPEND_BLOCKED_LAYERS = ("silver", "gold")


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


def _resolve_code_revision_for_manifest(
    *,
    resolved_config_hash: str,
    test_mode: bool,
) -> CodeRevisionProvenance:
    """Return code provenance, with a deterministic test-only fallback."""
    code_revision = get_code_revision_provenance()
    if code_revision.git_commit is not None or not test_mode:
        return code_revision
    return CodeRevisionProvenance(
        git_commit=f"test-{resolved_config_hash[:12]}",
        source_revision_state="clean",
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
    _validate_reproducible_sink_modes(
        yaml_config=yaml_config,
        strict_replay_requested=bool(getattr(ctx, "exact_replay", False))
        or required_persistence_profile in _STRICT_PERSISTENCE_PROFILES,
    )
    reproducibility_profile = resolve_reproducibility_family_profile(
        provider=provider,
        entity=entity,
        contract_ref=request_inputs.contract_ref,
        execution_context="source",
    )
    code_revision = _resolve_code_revision_for_manifest(
        resolved_config_hash=request_inputs.resolved_config_hash,
        test_mode=bool(getattr(inputs.settings, "test_mode", False)),
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
        git_commit=code_revision.git_commit,
        source_revision_state=code_revision.source_revision_state,
        config_hash=request_inputs.resolved_config_hash,
        resolved_config_hash=request_inputs.resolved_config_hash,
        effective_config_hash=request_inputs.effective_config_hash,
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
        strict_exact_replay_supported=(
            reproducibility_profile.strict_exact_replay_supported
        ),
    )
    return request


def _validate_reproducible_sink_modes(
    *,
    yaml_config: object,
    strict_replay_requested: bool,
) -> None:
    """Reject append-mode semantic outputs for strict reproducibility contexts."""
    if not strict_replay_requested:
        return
    sink = getattr(yaml_config, "sink", None)
    if not isinstance(sink, dict):
        return
    blocked: list[str] = []
    for layer_name in _REPRODUCIBLE_APPEND_BLOCKED_LAYERS:
        layer_config = sink.get(layer_name)
        if layer_config is None or not _sink_layer_enabled(layer_config):
            continue
        mode = _sink_layer_mode(layer_config)
        if mode == "append":
            blocked.append(f"sink.{layer_name}.mode=append")
    if blocked:
        details = ", ".join(blocked)
        raise RuntimeError(
            "Strict reproducibility contexts cannot use append-mode Silver/Gold "
            f"semantic outputs ({details}); use merge/upsert, overwrite, or SCD2 "
            "semantics with stable keys instead"
        )


def _sink_layer_enabled(layer_config: object) -> bool:
    if isinstance(layer_config, dict):
        return bool(layer_config.get("enabled", True))
    return bool(getattr(layer_config, "enabled", True))


def _sink_layer_mode(layer_config: object) -> str:
    raw_mode = (
        layer_config.get("mode", "")
        if isinstance(layer_config, dict)
        else getattr(layer_config, "mode", "")
    )
    return str(raw_mode or "").strip().lower()


def _validate_required_runtime_persistence_profile(
    *,
    request: RunManifestCreateSpec,
    required_persistence_profile: str,
    strict_exact_replay_supported: bool,
) -> None:
    strict_replay_requested = bool(request.launch_context.get("exact_replay"))
    if (
        required_persistence_profile not in {"replay_ready", "forensic_grade"}
        and not strict_replay_requested
    ):
        return
    if not strict_exact_replay_supported:
        raise RuntimeError(
            "Pipeline execution is outside the published strict exact-replay "
            "support boundary for this run family"
        )
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
    resolved_config_hash: str,
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

    manifest = RunManifestService(
        manifest_port=manifest_store,
        clock=SystemClock(),
    ).create_manifest(manifest_create_request)
    if ledger_service is not None:
        ledger_service.manifest_id = manifest.manifest_id
        ledger_service.record_manifest_created(manifest)
    control_plane_refs = _create_control_plane_refs(
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
