"""RunManifestCreateSpec assembly helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import bioetl.composition.runtime_builders.run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec,
)
from bioetl.composition.runtime_builders._run_manifest_attr_support import (
    read_attr as _read_attr,
)
from bioetl.composition.runtime_builders._silver_filter_compatibility_support import (
    current_silver_filter_compatibility_mode,
)
from bioetl.composition.services.versioning import get_pipeline_version
from bioetl.domain.control_plane import ReplayCapability

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders._run_manifest_creation_support import (
        _RunManifestCreateRequestInputs,
    )


def build_manifest_create_spec(
    *,
    request_inputs: _RunManifestCreateRequestInputs,
    source_refs: tuple[object, ...],
    replay_of_run_id: object,
    replay_of_manifest_id: object,
    code_revision: object,
    replay_capability: ReplayCapability,
    launch_context: dict[str, object],
) -> RunManifestCreateSpec:
    """Build one manifest creation spec from resolved runtime inputs."""
    ctx = request_inputs.ctx
    inputs = request_inputs.inputs
    runtime_config = _manifest_support.to_serializable_mapping(inputs.runtime_config)
    runtime_config.setdefault(
        "silver_filter_compatibility_mode",
        current_silver_filter_compatibility_mode(),
    )
    return RunManifestCreateSpec(
        run_id=ctx.run_id,
        run_type=_read_attr(ctx, "run_type", "incremental"),
        pipeline_name=ctx.pipeline_name,
        provider=request_inputs.provider,
        entity=request_inputs.entity,
        launch_context=launch_context,
        runtime_config=runtime_config,
        resolved_config=_manifest_support.to_serializable_mapping(inputs.yaml_config),
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        source_refs=source_refs,
        planned_artifacts=_manifest_support.build_planned_artifacts(
            settings=inputs.settings,
            provider=request_inputs.provider,
            entity=request_inputs.entity,
        ),
        pipeline_version=get_pipeline_version(inputs.yaml_config),
        git_commit=code_revision.git_commit,
        source_revision_state=code_revision.source_revision_state,
        dependency_lock_hash=code_revision.dependency_lock_hash,
        config_hash=request_inputs.config_hash,
        resolved_config_hash=request_inputs.resolved_config_hash,
        effective_config_hash=request_inputs.effective_config_hash,
        source_fingerprint=request_inputs.source_fingerprint,
        contract_ref=request_inputs.contract_ref,
        contract_version=request_inputs.contract_version,
        contract_schema_hash=request_inputs.contract_schema_hash,
        dq_policy_ref=request_inputs.dq_policy_ref,
        rule_bundle_version=request_inputs.rule_bundle_version,
        normalization_profile_ref=request_inputs.normalization_profile_ref,
        normalization_profile_version=request_inputs.normalization_profile_version,
        normalization_profile_hash=request_inputs.normalization_profile_hash,
        dq_contract_compatibility_hash=request_inputs.dq_contract_compatibility_hash,
        effective_config_artifact_id=request_inputs.effective_config_artifact_id,
        replay_capability=replay_capability,
    )


__all__ = ["build_manifest_create_spec"]
