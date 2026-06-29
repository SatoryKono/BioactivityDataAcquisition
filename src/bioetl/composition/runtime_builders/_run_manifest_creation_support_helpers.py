"""Private helpers for run-manifest creation orchestration support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec,
)
from bioetl.composition.runtime_builders._run_manifest_attr_support import (
    read_attr as _read_attr,
)
from bioetl.composition.runtime_builders._run_manifest_data_roots import (
    build_planned_artifacts,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    to_serializable_mapping,
)
from bioetl.domain.filtering.silver_filter_identity import (
    resolve_silver_filter_compatibility_mode,
)
from bioetl.composition.services.versioning import get_pipeline_version
from bioetl.domain.control_plane import ReplayCapability

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
        RunManifestContractIdentity,
    )
    from bioetl.domain.context import PipelineRunContext


@dataclass(frozen=True, slots=True)
class RunManifestCreateRequestInputs:
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


def current_silver_filter_compatibility_mode() -> str:
    """Expose a stable patch seam for run-manifest silver-filter compatibility."""
    return resolve_silver_filter_compatibility_mode()


def build_manifest_source_refs(
    *,
    manifest_support: object,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    required_persistence_profile: str,
) -> tuple[object, ...]:
    return manifest_support.build_run_source_refs(
        ctx=ctx,
        cached_bronze=inputs.cached_bronze,
        settings=inputs.settings,
        provider=provider,
        entity=entity,
        required_persistence_profile=required_persistence_profile,
    )


def assemble_manifest_create_spec(
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
