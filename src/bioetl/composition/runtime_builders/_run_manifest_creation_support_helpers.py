"""Private helpers for run-manifest creation orchestration support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.application.services.control_plane.ledger import RunLedgerService
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec,
)
from bioetl.composition.runtime_builders._run_manifest_planned_artifacts import (
    build_planned_artifacts,
)
from bioetl.composition.services.versioning import (
    CodeRevisionProvenance,
    get_pipeline_version,
)
from bioetl.composition.runtime_builders._snapshot_mapping_support import (
    to_serializable_mapping,
)
from bioetl.domain.filtering.silver_filter_identity import (
    resolve_silver_filter_compatibility_mode,
)
from bioetl.domain.control_plane import ReplayCapability, RunSourceRef

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
        ManifestReproducibilityContext,
    )
    from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
        RunManifestContractIdentity,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings


class _ManifestSourceRefBuilder(Protocol):
    def build_run_source_refs(
        self,
        *,
        ctx: PipelineRunContext,
        cached_bronze: object | None,
        settings: Settings,
        provider: str,
        entity: str,
        required_persistence_profile: str,
    ) -> tuple[RunSourceRef, ...]: ...


@dataclass(frozen=True, slots=True)
class RunManifestCreateRequestInputs:
    ctx: PipelineRunContext
    inputs: RunnerInputs
    provider: str
    entity: str
    reproducibility_context: ManifestReproducibilityContext
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
    manifest_support: _ManifestSourceRefBuilder,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    required_persistence_profile: str,
) -> tuple[RunSourceRef, ...]:
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
    request_inputs: RunManifestCreateRequestInputs,
    source_refs: tuple[RunSourceRef, ...],
    replay_of_run_id: str | None,
    replay_of_manifest_id: str | None,
    code_revision: CodeRevisionProvenance,
    replay_capability: ReplayCapability,
    launch_context: dict[str, object],
) -> RunManifestCreateSpec:
    """Build one manifest creation spec from resolved runtime inputs."""
    ctx = request_inputs.ctx
    inputs = request_inputs.inputs
    runtime_config = to_serializable_mapping(inputs.runtime_config)
    runtime_config.setdefault(
        "silver_filter_compatibility_mode",
        current_silver_filter_compatibility_mode(),
    )
    contract_identity = request_inputs.contract_identity
    provider = request_inputs.provider
    entity = request_inputs.entity
    return RunManifestCreateSpec(
        run_id=ctx.run_id,
        run_type=ctx.run_type,
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
        launch_context=launch_context,
        runtime_config=runtime_config,
        resolved_config=to_serializable_mapping(inputs.yaml_config),
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        workflow_run_id=ctx.workflow_run_id,
        workflow_name=ctx.workflow_name,
        workflow_step_id=ctx.workflow_step_id,
        source_refs=source_refs,
        planned_artifacts=build_planned_artifacts(
            settings=inputs.settings,
            provider=provider,
            entity=entity,
            run_id=str(ctx.run_id),
            pipeline_name=ctx.pipeline_name,
            workflow_id=ctx.workflow_id,
            debug_export_root=(
                ctx.debug_export_dir if ctx.debug_export_enabled else None
            ),
        ),
        pipeline_version=get_pipeline_version(inputs.yaml_config),
        git_commit=code_revision.git_commit,
        source_revision_state=code_revision.source_revision_state,
        dependency_lock_hash=code_revision.dependency_lock_hash,
        config_hash=request_inputs.config_hash,
        resolved_config_hash=request_inputs.resolved_config_hash,
        effective_config_hash=request_inputs.effective_config_hash,
        source_fingerprint=request_inputs.source_fingerprint,
        contract_ref=contract_identity.contract_ref,
        contract_version=contract_identity.contract_version,
        contract_schema_hash=contract_identity.contract_schema_hash,
        dq_policy_ref=contract_identity.dq_policy_ref,
        rule_bundle_version=contract_identity.rule_bundle_version,
        normalization_profile_ref=contract_identity.normalization_profile_ref,
        normalization_profile_version=contract_identity.normalization_profile_version,
        normalization_profile_hash=contract_identity.normalization_profile_hash,
        dq_contract_compatibility_hash=request_inputs.dq_contract_compatibility_hash,
        effective_config_artifact_id=request_inputs.effective_config_artifact_id,
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
