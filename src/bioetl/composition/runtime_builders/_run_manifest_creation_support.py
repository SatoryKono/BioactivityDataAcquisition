"""Private helpers for run-manifest creation orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

import bioetl.composition.runtime_builders.run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec,
)
from bioetl.composition.runtime_builders._run_manifest_attr_support import (
    read_attr as _read_attr,
)
from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    resolve_code_revision_for_manifest,
    validate_required_runtime_persistence_profile,
)
from bioetl.composition.runtime_builders._run_manifest_data_roots import (
    build_planned_artifacts,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    to_serializable_mapping,
)
from bioetl.composition.runtime_builders._silver_filter_compatibility_support import (
    current_silver_filter_compatibility_mode,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    RunManifestContractIdentity,
)
from bioetl.composition.services.versioning import get_pipeline_version
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    assess_reproducibility_policy,
)

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.domain.context import PipelineRunContext


@dataclass(frozen=True, slots=True)
class _RunManifestCreateRequestInputs:
    ctx: object
    inputs: object
    provider: str
    entity: str
    reproducibility_context: object
    run_type_value: str
    execution_context_value: str
    config_hash: str
    resolved_config_hash: str
    effective_config_hash: str
    source_fingerprint: str | None
    contract_identity: RunManifestContractIdentity
    dq_contract_compatibility_hash: str
    effective_config_artifact_id: str


def _validate_exact_replay_boundary(ctx: object, context: object) -> None:
    if not bool(_read_attr(ctx, "exact_replay", False)):
        return
    if bool(_read_attr(context, "strict_exact_replay_supported", False)):
        return
    raise RuntimeError(
        "Pipeline execution is outside the published strict exact-replay "
        "support boundary for this run family"
    )


def _build_manifest_source_refs(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    required_persistence_profile: str,
) -> tuple[object, ...]:
    return _manifest_support.build_run_source_refs(
        ctx=ctx,
        cached_bronze=inputs.cached_bronze,
        settings=inputs.settings,
        provider=provider,
        entity=entity,
        required_persistence_profile=required_persistence_profile,
    )


def _build_manifest_launch_context(
    *,
    request_inputs: object,
    reproducibility_context: object,
) -> dict[str, object]:
    return _manifest_support.build_launch_context_snapshot(
        _read_attr(request_inputs, "ctx"),
        run_type_value=_read_attr(request_inputs, "run_type_value"),
        execution_context_value=_read_attr(request_inputs, "execution_context_value"),
        configured_required_persistence_profile=_read_attr(
            reproducibility_context, "configured_required_persistence_profile"
        ),
        required_persistence_profile=_read_attr(
            reproducibility_context, "required_persistence_profile"
        ),
        required_persistence_profile_opt_down=bool(
            _read_attr(
                reproducibility_context,
                "required_persistence_profile_opt_down",
                False,
            )
        ),
        strict_exact_replay_supported=_read_attr(
            reproducibility_context, "strict_exact_replay_supported"
        ),
        reproducibility_family=_read_attr(reproducibility_context, "family"),
        replay_family_contract=_read_attr(
            reproducibility_context, "replay_family_contract"
        ),
        strict_replay_runtime_verdict=_read_attr(
            reproducibility_context, "strict_replay_runtime_verdict"
        ),
        replay_support_scope=_read_attr(reproducibility_context, "support_scope"),
        replay_support_reason=_read_attr(reproducibility_context, "reason"),
    )


def _build_replay_assessment(
    *,
    request_inputs: object,
    reproducibility_context: object,
    source_refs: tuple[object, ...],
    replay_capability: ReplayCapability,
) -> object:
    return assess_reproducibility_policy(
        source_refs=source_refs,
        required_persistence_profile=_read_attr(
            reproducibility_context, "required_persistence_profile"
        ),
        strict_exact_replay_supported=_read_attr(
            reproducibility_context, "strict_exact_replay_supported"
        ),
        exact_replay_requested=bool(
            _read_attr(_read_attr(request_inputs, "ctx"), "exact_replay", False)
        ),
        resume_requested=bool(
            _read_attr(_read_attr(request_inputs, "ctx"), "resume", False)
        ),
        replay_capability=replay_capability,
        run_type=_read_attr(request_inputs, "run_type_value"),
        debug_only=bool(
            _read_attr(
                _read_attr(_read_attr(request_inputs, "inputs"), "settings"),
                "debug",
                False,
            )
        ),
    )


def _apply_replay_assessment(
    launch_context: dict[str, object],
    replay_assessment: object,
) -> None:
    replay_verdict = _read_attr(replay_assessment, "replay_readiness_verdict").value
    launch_context.update(
        {
            "replay_readiness_verdict": replay_verdict,
            "exact_replay_ready": replay_verdict == "exact_replay_ready",
            "replay_blockers": list(_read_attr(replay_assessment, "blocking_gaps")),
        }
    )


def _assemble_manifest_create_spec(
    *,
    request_inputs: object,
    source_refs: tuple[object, ...],
    replay_of_run_id: object,
    replay_of_manifest_id: object,
    code_revision: object,
    replay_capability: ReplayCapability,
    launch_context: dict[str, object],
) -> RunManifestCreateSpec:
    """Build one manifest creation spec from resolved runtime inputs."""
    ctx = _read_attr(request_inputs, "ctx")
    inputs = _read_attr(request_inputs, "inputs")
    runtime_config = to_serializable_mapping(_read_attr(inputs, "runtime_config"))
    runtime_config.setdefault(
        "silver_filter_compatibility_mode",
        current_silver_filter_compatibility_mode(),
    )
    contract_identity = _read_attr(request_inputs, "contract_identity")
    provider = _read_attr(request_inputs, "provider")
    entity = _read_attr(request_inputs, "entity")
    return RunManifestCreateSpec(
        run_id=ctx.run_id,
        run_type=_read_attr(ctx, "run_type", "incremental"),
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
        launch_context=launch_context,
        runtime_config=runtime_config,
        resolved_config=to_serializable_mapping(_read_attr(inputs, "yaml_config")),
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        source_refs=source_refs,
        planned_artifacts=build_planned_artifacts(
            settings=_read_attr(inputs, "settings"),
            provider=provider,
            entity=entity,
            run_id=str(ctx.run_id),
            pipeline_name=ctx.pipeline_name,
            workflow_id=str(getattr(ctx, "workflow_id", "standalone")),
            debug_export_root=(
                getattr(ctx, "debug_export_dir", None)
                if bool(getattr(ctx, "debug_export_enabled", False))
                else None
            ),
        ),
        pipeline_version=get_pipeline_version(_read_attr(inputs, "yaml_config")),
        git_commit=code_revision.git_commit,
        source_revision_state=code_revision.source_revision_state,
        dependency_lock_hash=code_revision.dependency_lock_hash,
        config_hash=_read_attr(request_inputs, "config_hash"),
        resolved_config_hash=_read_attr(request_inputs, "resolved_config_hash"),
        effective_config_hash=_read_attr(request_inputs, "effective_config_hash"),
        source_fingerprint=_read_attr(request_inputs, "source_fingerprint"),
        contract_ref=contract_identity.contract_ref,
        contract_version=contract_identity.contract_version,
        contract_schema_hash=contract_identity.contract_schema_hash,
        dq_policy_ref=contract_identity.dq_policy_ref,
        rule_bundle_version=contract_identity.rule_bundle_version,
        normalization_profile_ref=contract_identity.normalization_profile_ref,
        normalization_profile_version=contract_identity.normalization_profile_version,
        normalization_profile_hash=contract_identity.normalization_profile_hash,
        dq_contract_compatibility_hash=_read_attr(
            request_inputs, "dq_contract_compatibility_hash"
        ),
        effective_config_artifact_id=_read_attr(
            request_inputs, "effective_config_artifact_id"
        ),
        replay_capability=replay_capability,
    )


def create_ledger_service(
    inputs: RunnerInputs,
    ctx: PipelineRunContext,
) -> RunLedgerService | None:
    """Build the optional run-ledger service for manifest publication."""
    from bioetl.composition.bootstrap.control_plane_store_builders import (
        create_run_ledger_store,
    )
    from bioetl.composition.occurrence_identity import create_runtime_occurrence_id

    return RunLedgerService(
        ledger_port=create_run_ledger_store(
            settings=inputs.settings,
            metrics=inputs.observability.metrics,
        ),
        manifest_id="pending",
        run_id=ctx.run_id,
        _entry_id_factory=lambda: create_runtime_occurrence_id("run_ledger_entry"),
    )


def build_manifest_create_request(
    request_inputs: _RunManifestCreateRequestInputs,
) -> RunManifestCreateSpec:
    """Build the canonical RunManifest create request."""
    ctx = request_inputs.ctx
    inputs = request_inputs.inputs
    reproducibility_context = request_inputs.reproducibility_context
    _validate_exact_replay_boundary(ctx, reproducibility_context)
    source_refs = _build_manifest_source_refs(
        ctx=ctx,
        inputs=inputs,
        provider=request_inputs.provider,
        entity=request_inputs.entity,
        required_persistence_profile=_read_attr(
            reproducibility_context, "required_persistence_profile"
        ),
    )
    replay_of_run_id, replay_of_manifest_id = (
        _manifest_support.resolve_replay_parentage(
            ctx=ctx,
            runtime_config=inputs.runtime_config,
        )
    )
    replay_capability = _manifest_support.resolve_replay_capability(
        source_refs=source_refs,
        resume_requested=bool(_read_attr(ctx, "resume", False)),
    )
    launch_context = _build_manifest_launch_context(
        request_inputs=request_inputs,
        reproducibility_context=reproducibility_context,
    )
    replay_assessment = _build_replay_assessment(
        request_inputs=request_inputs,
        reproducibility_context=reproducibility_context,
        source_refs=source_refs,
        replay_capability=replay_capability,
    )
    _apply_replay_assessment(launch_context, replay_assessment)
    request = _assemble_manifest_create_spec(
        request_inputs=request_inputs,
        source_refs=source_refs,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        code_revision=resolve_code_revision_for_manifest(
            resolved_config_hash=request_inputs.resolved_config_hash,
            test_mode=bool(_read_attr(inputs.settings, "test_mode", False)),
        ),
        replay_capability=replay_capability,
        launch_context=launch_context,
    )
    validate_required_runtime_persistence_profile(
        request=request,
        required_persistence_profile=_read_attr(
            reproducibility_context, "required_persistence_profile"
        ),
        strict_exact_replay_supported=_read_attr(
            reproducibility_context, "strict_exact_replay_supported", False
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
    increment_counter = _read_attr(metrics, "increment_counter", None)
    if not callable(increment_counter):
        return
    set_gauge = _read_attr(metrics, "set_gauge", None)
    launch_context = request.launch_context
    strict_replay_requested = bool(
        launch_context.get("exact_replay", False)
        if isinstance(launch_context, Mapping)
        else _read_attr(launch_context, "exact_replay", False)
    )
    required_persistence_profile = str(
        (
            launch_context.get("required_persistence_profile")
            if isinstance(launch_context, Mapping)
            else _read_attr(launch_context, "required_persistence_profile")
        )
        or DEFAULT_REQUIRED_PERSISTENCE_PROFILE
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
    raw_run_type = _read_attr(request.run_type, "value", request.run_type)
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
