"""Private helpers for run-manifest request/spec assembly."""

from __future__ import annotations

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
from bioetl.composition.runtime_builders._silver_filter_compatibility_support import (
    current_silver_filter_compatibility_mode,
)
from bioetl.composition.services.versioning import get_pipeline_version
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_policy import (
    assess_reproducibility_policy,
)


def _build_manifest_launch_context(
    *,
    request_inputs: object,
    reproducibility_context: object,
) -> dict[str, object]:
    from bioetl.composition.runtime_builders import run_manifest_support as _manifest_support

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
