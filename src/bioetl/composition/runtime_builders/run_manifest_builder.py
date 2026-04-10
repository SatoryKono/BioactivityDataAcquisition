"""Run manifest creation for control-plane."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.application.services.run_manifest_service import (
    RunManifestCreateRequest,
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
    resolve_replay_capability as _resolve_replay_capability,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_provider_entity as _resolve_provider_entity,
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
from bioetl.infrastructure.control_plane import FileRunManifestStore

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext

def _create_ledger_service(
    inputs: RunnerInputs,
    ctx: PipelineRunContext,
) -> RunLedgerService | None:
    """Create ledger service if enabled."""
    from bioetl.application.services.run_ledger_service import RunLedgerService
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
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    run_type_value: str,
    execution_context_value: str,
    effective_config_hash: str,
    contract_ref: str,
    contract_version: str | None,
    contract_schema_hash: str | None,
    dq_policy_ref: str | None,
    rule_bundle_version: str | None,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
) -> RunManifestCreateRequest:
    """Build the manifest create request."""
    yaml_config = inputs.yaml_config
    source_refs = _build_run_source_refs(
        ctx=ctx,
        cached_bronze=inputs.cached_bronze,
        settings=inputs.settings,
        provider=provider,
        entity=entity,
    )
    return RunManifestCreateRequest(
        run_id=ctx.run_id,
        run_type=getattr(ctx, "run_type", "incremental"),
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
        launch_context=_build_launch_context_snapshot(
            ctx,
            run_type_value=run_type_value,
            execution_context_value=execution_context_value,
        ),
        runtime_config=_to_serializable_mapping(inputs.runtime_config),
        resolved_config=_to_serializable_mapping(yaml_config),
        source_refs=source_refs,
        planned_artifacts=_build_planned_artifacts(
            settings=inputs.settings,
            provider=provider,
            entity=entity,
        ),
        pipeline_version=get_pipeline_version(yaml_config),
        git_commit=get_git_commit(),
        config_hash=effective_config_hash,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        replay_capability=_resolve_replay_capability(source_refs),
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
    """Create immutable manifest before pipeline assembly begins."""
    yaml_config = inputs.yaml_config

    # Resolve context values
    run_type_value, execution_context_value = _resolve_run_context_values(ctx)

    # Resolve provider and entity
    provider, entity = _resolve_provider_entity(
        pipeline_name=ctx.pipeline_name,
        yaml_config=yaml_config,
    )

    # Resolve contract identity
    (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    ) = _resolve_contract_identity(provider=provider, entity=entity)

    # Create manifest store
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(inputs.settings, "run_manifest"),
        metrics=inputs.observability.metrics,
    )

    # Create ledger service if enabled
    ledger_service: RunLedgerService | None = None
    if ledger_enabled:
        ledger_service = _create_ledger_service(inputs, ctx)

    # Build and create manifest
    manifest_create_request = _build_manifest_create_request(
        ctx,
        inputs,
        provider,
        entity,
        run_type_value,
        execution_context_value,
        effective_config_hash,
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
        dq_contract_compatibility_hash,
        effective_config_artifact_id,
    )

    manifest = RunManifestService(manifest_port=manifest_store).create_manifest(
        manifest_create_request
    )

    # Update ledger service with manifest ID
    if ledger_service is not None:
        ledger_service.manifest_id = manifest.manifest_id
        ledger_service.record_manifest_created(manifest)

    # Create control plane references
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
