"""Typed source and drilldown metadata for Control Plane identity anchors."""

from __future__ import annotations

from bioetl.interfaces.http.control_plane_identity.types import (
    AnchorSourceModel,
    DrilldownTarget,
)

DEFAULT_SOURCE_MODEL = AnchorSourceModel(
    source_type="derived_identity_evidence",
    source_quality="derived",
)
DEFAULT_DRILLDOWN_TARGET = DrilldownTarget(
    target_type="identity_evidence",
    target_template="identity_evidence.details",
    label="Identity evidence details",
)

SOURCE_MODEL_BY_NAME: dict[str, AnchorSourceModel] = {
    "run_id": AnchorSourceModel("run_manifest", "authoritative"),
    "manifest_id": AnchorSourceModel("run_manifest", "authoritative"),
    "pipeline_name": AnchorSourceModel("run_manifest", "authoritative"),
    "provider_entity": AnchorSourceModel("run_manifest", "derived"),
    "runtime_mode": AnchorSourceModel("run_manifest_runtime_config", "derived"),
    "execution_fingerprint": AnchorSourceModel(
        "run_manifest_identity_graph", "authoritative"
    ),
    "git_commit": AnchorSourceModel("run_manifest_code_provenance", "authoritative"),
    "pipeline_version": AnchorSourceModel(
        "run_manifest_code_provenance", "authoritative"
    ),
    "effective_config_hash": AnchorSourceModel(
        "effective_config_artifact", "authoritative"
    ),
    "effective_config_artifact_id": AnchorSourceModel(
        "effective_config_artifact", "authoritative"
    ),
    "contract_ref": AnchorSourceModel("contract_registry", "authoritative"),
    "contract_version": AnchorSourceModel("contract_registry", "authoritative"),
    "contract_schema_hash": AnchorSourceModel("contract_registry", "authoritative"),
    "input_snapshot_identity_fingerprint": AnchorSourceModel(
        "input_snapshots", "derived"
    ),
    "input_snapshot_count": AnchorSourceModel("input_snapshots", "derived"),
    "replay_mode": AnchorSourceModel("run_manifest_replay_parentage", "derived"),
    "replay_of_run_id": AnchorSourceModel(
        "run_manifest_replay_parentage", "authoritative"
    ),
    "replay_of_manifest_id": AnchorSourceModel(
        "run_manifest_replay_parentage", "authoritative"
    ),
    "checkpoint_anchor_status": AnchorSourceModel(
        "checkpoint_metadata_compare", "derived"
    ),
    "composite_run_identity": AnchorSourceModel("checkpoint_metadata", "authoritative"),
    "identity_graph_complete": AnchorSourceModel(
        "identity_graph_diagnostics", "derived"
    ),
    "config_hash": AnchorSourceModel("run_manifest_code_provenance", "authoritative"),
    "dq_policy_ref": AnchorSourceModel("contract_registry", "authoritative"),
    "rule_bundle_version": AnchorSourceModel("contract_registry", "authoritative"),
    "dq_contract_compatibility_hash": AnchorSourceModel(
        "contract_registry", "authoritative"
    ),
    "source_refs": AnchorSourceModel("run_manifest_source_refs", "authoritative"),
    "input_snapshot_ids": AnchorSourceModel("input_snapshots", "authoritative"),
    "input_snapshot_content_hashes": AnchorSourceModel(
        "input_snapshots", "authoritative"
    ),
    "replay_capability": AnchorSourceModel(
        "run_manifest_replay_policy", "authoritative"
    ),
    "exact_replay_eligible": AnchorSourceModel("identity_graph_diagnostics", "derived"),
    "resume_contract": AnchorSourceModel("identity_graph_diagnostics", "reported"),
    "lineage_fragment_ids": AnchorSourceModel("run_ledger", "reported"),
    "artifact_refs": AnchorSourceModel("run_ledger_artifacts", "reported"),
    "latest_event_id": AnchorSourceModel("run_ledger", "reported"),
    "launch_context_hash": AnchorSourceModel("run_manifest_launch_context", "derived"),
    "runtime_config_hash": AnchorSourceModel("run_manifest_runtime_config", "derived"),
    "planned_artifacts": AnchorSourceModel(
        "run_manifest_planned_artifacts", "authoritative"
    ),
    "published_artifacts": AnchorSourceModel("run_ledger_artifacts", "reported"),
    "component_run_ids": AnchorSourceModel("run_ledger_composite_events", "reported"),
    "checkpoint_file_id": AnchorSourceModel("checkpoint_metadata", "reported"),
    "lock_owner_id": AnchorSourceModel("runtime_lock_metadata", "reported"),
    "dq_report_paths": AnchorSourceModel("dq_diagnostics", "reported"),
    "cross_validation_rule_ids": AnchorSourceModel("composite_diagnostics", "reported"),
    "bronze_batch_ids": AnchorSourceModel("source_refs_lineage", "derived"),
}

DRILLDOWN_TARGET_BY_NAME: dict[str, DrilldownTarget] = {
    "run_id": DrilldownTarget(
        "run_manifest", "manifest.by_run_id:{value}", "Run manifest by run_id"
    ),
    "manifest_id": DrilldownTarget(
        "run_manifest", "manifest.by_manifest_id:{value}", "Run manifest JSON"
    ),
    "pipeline_name": DrilldownTarget(
        "dashboard", "dashboard.pipeline:{value}", "Pipeline dashboard"
    ),
    "provider_entity": DrilldownTarget(
        "lineage", "lineage.dataset:{value}", "Dataset lineage"
    ),
    "runtime_mode": DrilldownTarget(
        "manifest_section", "manifest.runtime_config", "Manifest runtime config"
    ),
    "execution_fingerprint": DrilldownTarget(
        "identity_graph",
        "identity_graph.execution_fingerprint:{value}",
        "Execution fingerprint diagnostics",
    ),
    "git_commit": DrilldownTarget(
        "repository", "repository.commit:{value}", "Repository commit"
    ),
    "pipeline_version": DrilldownTarget(
        "pipeline_spec", "pipeline.version:{value}", "Pipeline spec"
    ),
    "effective_config_hash": DrilldownTarget(
        "effective_config", "effective_config.hash:{value}", "Effective config diff"
    ),
    "effective_config_artifact_id": DrilldownTarget(
        "effective_config",
        "effective_config.artifact:{value}",
        "Effective config artifact",
    ),
    "contract_ref": DrilldownTarget(
        "contract_registry", "contract.ref:{value}", "Contract registry entry"
    ),
    "contract_version": DrilldownTarget(
        "contract_registry", "contract.version:{value}", "Contract version"
    ),
    "contract_schema_hash": DrilldownTarget(
        "contract_registry", "contract.schema_hash:{value}", "Contract schema diff"
    ),
    "input_snapshot_identity_fingerprint": DrilldownTarget(
        "input_snapshots",
        "input_snapshots.fingerprint:{value}",
        "Input snapshot closure",
    ),
    "input_snapshot_count": DrilldownTarget(
        "input_snapshots", "input_snapshots.table", "Input snapshot table"
    ),
    "replay_mode": DrilldownTarget(
        "replay_diagnostics", "replay.mode:{value}", "Replay diagnostics"
    ),
    "replay_of_run_id": DrilldownTarget(
        "run_manifest", "manifest.parent_run_id:{value}", "Parent run manifest"
    ),
    "replay_of_manifest_id": DrilldownTarget(
        "run_manifest", "manifest.parent_manifest_id:{value}", "Parent manifest"
    ),
    "checkpoint_anchor_status": DrilldownTarget(
        "checkpoint_compare", "checkpoint.compare", "Checkpoint compare"
    ),
    "composite_run_identity": DrilldownTarget(
        "checkpoint_compare",
        "checkpoint.composite_run_identity:{value}",
        "Composite checkpoint details",
    ),
    "identity_graph_complete": DrilldownTarget(
        "identity_gaps", "identity_graph.gaps", "Identity gaps table"
    ),
    "config_hash": DrilldownTarget(
        "manifest_section",
        "manifest.code_provenance.config_hash:{value}",
        "Source config diff",
    ),
    "dq_policy_ref": DrilldownTarget(
        "contract_registry", "dq.policy:{value}", "DQ policy"
    ),
    "rule_bundle_version": DrilldownTarget(
        "contract_registry", "dq.rule_bundle:{value}", "DQ rule bundle"
    ),
    "dq_contract_compatibility_hash": DrilldownTarget(
        "contract_registry", "dq.compatibility_hash:{value}", "DQ contract diff"
    ),
    "source_refs": DrilldownTarget(
        "source_refs", "manifest.source_refs", "Source refs"
    ),
    "input_snapshot_ids": DrilldownTarget(
        "input_snapshots", "input_snapshots.ids:{value}", "Input snapshot details"
    ),
    "input_snapshot_content_hashes": DrilldownTarget(
        "input_snapshots", "input_snapshots.hashes:{value}", "Input snapshot hash diff"
    ),
    "replay_capability": DrilldownTarget(
        "replay_diagnostics", "replay.capability:{value}", "Replay capability"
    ),
    "exact_replay_eligible": DrilldownTarget(
        "replay_diagnostics", "replay.exact_eligible:{value}", "Exact replay blockers"
    ),
    "resume_contract": DrilldownTarget(
        "checkpoint_compare", "checkpoint.resume_contract", "Resume contract"
    ),
    "lineage_fragment_ids": DrilldownTarget(
        "lineage", "lineage.fragments:{value}", "Lineage fragments"
    ),
    "artifact_refs": DrilldownTarget(
        "artifacts", "artifacts.refs:{value}", "Published artifacts"
    ),
    "latest_event_id": DrilldownTarget(
        "run_ledger", "ledger.event:{value}", "Run ledger event"
    ),
    "launch_context_hash": DrilldownTarget(
        "manifest_section", "manifest.launch_context", "Launch context"
    ),
    "runtime_config_hash": DrilldownTarget(
        "manifest_section", "manifest.runtime_config", "Runtime config"
    ),
    "planned_artifacts": DrilldownTarget(
        "artifacts", "artifacts.planned:{value}", "Planned artifacts"
    ),
    "published_artifacts": DrilldownTarget(
        "artifacts", "artifacts.published:{value}", "Published artifacts"
    ),
    "component_run_ids": DrilldownTarget(
        "run_manifest", "manifest.component_runs:{value}", "Component runs"
    ),
    "checkpoint_file_id": DrilldownTarget(
        "checkpoint_raw", "checkpoint.file:{value}", "Raw checkpoint"
    ),
    "lock_owner_id": DrilldownTarget(
        "runtime_locks", "runtime_lock:{value}", "Runtime lock"
    ),
    "dq_report_paths": DrilldownTarget("dq_reports", "dq.report:{value}", "DQ report"),
    "cross_validation_rule_ids": DrilldownTarget(
        "composite_diagnostics",
        "composite.cross_validation:{value}",
        "Cross-validation details",
    ),
    "bronze_batch_ids": DrilldownTarget(
        "lineage", "lineage.bronze_batches:{value}", "Bronze lineage"
    ),
}


def source_model_for(anchor_name: str) -> AnchorSourceModel:
    """Return static source classification for an anchor."""
    return SOURCE_MODEL_BY_NAME.get(anchor_name, DEFAULT_SOURCE_MODEL)


def drilldown_target_for(anchor_name: str, value_full: str) -> DrilldownTarget:
    """Return typed drilldown metadata with the current anchor value applied."""
    target = DRILLDOWN_TARGET_BY_NAME.get(anchor_name, DEFAULT_DRILLDOWN_TARGET)
    return DrilldownTarget(
        target_type=target.target_type,
        target_template=target.target_template.format(value=value_full),
        label=target.label,
    )
