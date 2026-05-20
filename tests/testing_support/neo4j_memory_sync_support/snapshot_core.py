"""Core snapshot surface assertions for Neo4j memory sync."""

from __future__ import annotations

from .common import *  # noqa: F401,F403

def test_snapshot_contains_core_repo_surfaces() -> None:
    _, snapshot = _snapshot()
    node_keys = {(key.label, key.name) for key in snapshot.nodes}

    assert ("project", "BioETL") in node_keys
    assert ("repo_zone", "src") in node_keys
    assert ("repo_zone", "docs") in node_keys
    assert ("repo_zone", REPO_ZONE_GITHUB) in node_keys
    assert ("directory_surface", APPLICATION_CORE_DIR) in node_keys
    assert ("directory_surface", CHEMBL_CONFIG_DIR) in node_keys
    assert ("directory_surface", TESTS_ARCHITECTURE_DIR) in node_keys
    assert ("directory_surface", ARCHITECTURE_DIAGRAMS_DIR) in node_keys
    assert ("directory_surface", SCRIPTS_OPS_DIR) in node_keys
    assert ("directory_surface", GRAFANA_DASHBOARDS_DIR) in node_keys
    assert ("directory_surface", GITHUB_WORKFLOWS_DIR) in node_keys
    assert (
        "file_surface",
        RECORD_NORMALIZATION_PROCESSOR_PATH,
    ) in node_keys
    assert ("file_surface", CHEMBL_ACTIVITY_CONFIG_PATH) in node_keys
    assert ("file_surface", ARCHITECTURE_DIAGRAMS_README_PATH) in node_keys
    assert ("file_surface", SCRIPTS_MEMORY_MAIN_PATH) in node_keys
    assert ("file_surface", DIAGRAM_QUALITY_GATES_TEST_PATH) in node_keys
    assert ("file_surface", BIOETL_RUNTIME_DASHBOARD_PATH) in node_keys
    assert ("file_surface", TESTS_WORKFLOW_PATH) in node_keys
    assert ("layer_family", "domain") in node_keys
    assert ("package_family", "domain/ports") in node_keys
    assert (
        "module_surface",
        "src/bioetl/domain/config/pipeline.py",
    ) in node_keys
    assert (
        "class_surface",
        "src.bioetl.infrastructure.adapters.base.BaseHttpAdapter",
    ) in node_keys
    assert (
        "function_surface",
        "src.bioetl.domain.normalization.profiles.chembl_activity.create_case_normalizer",
    ) in node_keys
    assert (
        "method_surface",
        "src.bioetl.application.composite.merger.MergeService.merge",
    ) in node_keys
    assert any(label == "retirement_candidate" for label, _ in node_keys)
    assert any(label == "complexity_candidate" for label, _ in node_keys)
    assert ("provider_surface", "chembl") in node_keys
    assert ("entity_config", "chembl_activity") in node_keys
    assert ("composite_config", "composite_activity") in node_keys
    assert ("storage_surface", SILVER_CHEMBL_ACTIVITY) in node_keys
    assert ("storage_surface", SILVER_COMPOSITE_ACTIVITY) in node_keys
    assert ("storage_surface", RUN_MANIFEST_STORAGE_PATH) in node_keys
    assert ("storage_surface", EFFECTIVE_CONFIG_STORAGE_PATH) in node_keys
    assert ("storage_surface", LINEAGE_FRAGMENT_STORAGE_PATH) in node_keys
    assert ("dashboard_surface", "bioetl-overview-v2") in node_keys
    assert ("doc_source_surface", ARCHITECTURE_DIAGRAMS_HUB) in node_keys
    assert ("doc_source_surface", "diagram governance workflow") in node_keys
    assert ("doc_source_surface", "normalization plan") in node_keys
    assert ("doc_source_surface", "pipeline normalization matrix") in node_keys
    assert ("policy_surface", INTEGRATION_VCR_POLICY) in node_keys
    assert ("policy_surface", DIAGRAM_GOVERNANCE_POLICY) in node_keys
    assert ("script_surface", "scripts/engineering/dev/run_pytest.sh") in node_keys
    assert ("script_surface", "scripts/diagrams/__main__.py") in node_keys
    assert ("script_surface", "scripts/docs/__main__.py") in node_keys
    assert ("script_surface", "scripts/schema/__main__.py") in node_keys
    assert ("script_surface", SCRIPTS_MEMORY_MAIN_PATH) in node_keys
    assert ("script_surface", "scripts/engineering/qa/__main__.py") in node_keys
    assert ("port_surface", "bioetl.domain.ports") in node_keys
    assert (
        "port_surface",
        "bioetl.domain.ports.runtime.runner.RunnablePort",
    ) in node_keys
    assert ("adapter_surface", CHEMBL_ADAPTER_SURFACE) in node_keys
    assert ("adapter_impl_surface", CHEMBL_ADAPTER_IMPL_SURFACE) in node_keys
    assert ("pipeline_surface", "chembl_activity") in node_keys
    assert ("contract_surface", CONTRACT_CHEMBL_ACTIVITY) in node_keys
    assert ("alert_surface", "BioETLPipelineRunFailed") in node_keys
    assert ("runtime_evidence_surface", "run_manifest") in node_keys
    assert ("runtime_evidence_surface", "run_ledger") in node_keys
    assert ("runtime_evidence_surface", "effective_config_artifact") in node_keys
    assert ("runtime_evidence_surface", "lineage") in node_keys
    assert ("control_plane_artifact_surface", ARTIFACT_RUN_MANIFEST) in node_keys
    assert (
        "control_plane_artifact_surface",
        ARTIFACT_EFFECTIVE_CONFIG,
    ) in node_keys
    assert ("control_plane_artifact_surface", ARTIFACT_LINEAGE) in node_keys
    assert ("run_instance_surface", "manifest-left") in node_keys
    assert ("run_instance_surface", "manifest-chain-smoke") in node_keys
    assert ("run_instance_surface", "manifest-chain-2") in node_keys
    assert ("run_instance_surface", "manifest-composite-quarantine") in node_keys
    assert ("runtime_state_surface", "manifest-left::active-window") in node_keys
    assert ("runtime_state_surface", STATE_MANIFEST_CHAIN_2) in node_keys
    assert ("runtime_state_surface", "chembl_activity::composite-lock") in node_keys
    assert ("schema_field_surface", SILVER_CHEMBL_ACTIVITY_FIELD) in node_keys
    assert ("schema_field_surface", "gold/chembl/assay::_version") in node_keys
    assert ("schema_field_surface", SILVER_COMPOSITE_ACTIVITY_FIELD) in node_keys
    assert ("workflow_surface", "tests") in node_keys
    assert ("workflow_job_surface", JOB_GOVERNANCE_PREFLIGHT) in node_keys
    assert any(label == "workflow_call_surface" for label, _ in node_keys)
    assert any(label == "workflow_matrix_variant_surface" for label, _ in node_keys)
    assert any(label == "workflow_output_surface" for label, _ in node_keys)
    assert ("workflow_action_surface", ACTION_UPLOAD_ARTIFACT) in node_keys
    assert ("workflow_action_surface", "./.github/actions/setup-python-uv") in node_keys
    assert (
        "workflow_artifact_surface",
        ARTIFACT_COVERAGE_DATA,
    ) in node_keys
    assert ("workflow_secret_surface", "GITHUB_TOKEN") in node_keys
    assert ("cli_command_surface", CMD_BIOETL_RUN) in node_keys
    assert ("cli_command_surface", CMD_MEMORY_SYNC) in node_keys
    assert ("cli_command_surface", "scripts.docs verify") in node_keys
    assert any(label == "cli_option_surface" for label, _ in node_keys)
    assert any(label == "doc_claim_surface" for label, _ in node_keys)
    assert ("execution_path", EXEC_BIOETL_RUN) in node_keys
    assert ("execution_path", EXEC_DIAGRAMS_LINT) in node_keys
    assert ("execution_path", EXEC_DOCS_VERIFY) in node_keys
    assert (
        "execution_path",
        EXEC_SCHEMA_VALIDATE,
    ) in node_keys
    assert (
        "execution_path",
        "uv run python -m scripts.docs generate-pipeline-normalization-matrix --check",
    ) in node_keys
    assert (
        "execution_path",
        f"python -m scripts.memory sync --report {LEGACY_REPORT_PATH}",
    ) in node_keys
    assert (
        "execution_path",
        "python -m scripts.engineering.qa report-normalization-fallback-inventory --limit 20",
    ) in node_keys
    assert ("quality_gate", QUALITY_GATE_DIAGRAMS) in node_keys
    assert any(label == "duplication_cluster" for label, _ in node_keys)
    assert (
        "test_artifact",
        "tests/unit/scripts/ops/neo4j_memory_sync/test_snapshot_topology.py",
    ) in node_keys
    assert ("package_family", "composition/__pycache__") not in node_keys
    assert ("package_family", "infrastructure/__pycache__") not in node_keys
    assert ("package_family", "interfaces/__pycache__") not in node_keys
    assert ("directory_surface", "docs/99-archive") not in node_keys
    assert ("directory_surface", "docs/reports/generated") not in node_keys
    assert ("directory_surface", "scripts/archive") not in node_keys
    assert (
        "directory_surface",
        "docs/02-architecture/diagrams/views/svg",
    ) not in node_keys
    assert ("package_family", "composition/control_plane_api.py") not in node_keys
    assert ("package_family", "interfaces/test_cli_checkpoint_list.py") not in node_keys
    assert any(
        node.properties.get("current_cycle_status") == "current_cycle"
        for node in snapshot.nodes.values()
        if node.key.label
        in {"module_surface", "class_surface", "function_surface", "method_surface"}
    )

    silver_assay = snapshot.nodes[NodeKey("storage_surface", "silver/chembl/assay")]
    assert silver_assay.properties["partition_by"] == ["assay_type"]
    assert silver_assay.properties["schema_present"] is True
    assert silver_assay.properties["schema_include_groups"] == [
        "system",
        "business",
        "dq",
    ]
    assert silver_assay.properties["quality_version"] == "1.1.0"
    assert silver_assay.properties["retention_days"] == 7
    assert silver_assay.properties["storage_roles"] == ["entity_layer_output"]

    gold_assay = snapshot.nodes[NodeKey("storage_surface", "gold/chembl/assay")]
    assert gold_assay.properties["versioning_mode"] == "scd2"
    assert gold_assay.properties["version_column"] == "_version"
    assert gold_assay.properties["current_flag_column"] == "_is_current"
    assert gold_assay.properties["valid_from_column"] == "_valid_from"
    assert gold_assay.properties["valid_to_column"] == "_valid_to"

    shared_activity = snapshot.nodes[NodeKey("storage_surface", SILVER_CHEMBL_ACTIVITY)]
    assert sorted(shared_activity.properties["storage_roles"]) == [
        "composite_seed_input",
        "entity_layer_output",
    ]

    composite_activity = snapshot.nodes[
        NodeKey("storage_surface", SILVER_COMPOSITE_ACTIVITY)
    ]
    assert composite_activity.properties["config_version"] == "1.0.0"
    assert composite_activity.properties["merge_strategy"] == "left_outer"
    assert composite_activity.properties["sort_by"] == ["entity_id", "activity_id"]

    manifest_left = snapshot.nodes[NodeKey("run_instance_surface", "manifest-left")]
    assert manifest_left.properties["run_id"] == "00000000-0000-0000-0000-000000000301"
    assert manifest_left.properties["execution_fingerprint"] == "fp-stable"
    assert manifest_left.properties["contract_version"] == "1.0.0"
    assert manifest_left.properties["effective_config_artifact_id"] == "eca-123"

    chain_smoke = snapshot.nodes[
        NodeKey("run_instance_surface", "manifest-chain-smoke")
    ]
    assert chain_smoke.properties["lifecycle_status"] == "success"
    assert chain_smoke.properties["lineage_fragment_id"] == "silver:fragment-smoke-1"

    composite_quarantine = snapshot.nodes[
        NodeKey("run_instance_surface", "manifest-composite-quarantine")
    ]
    assert composite_quarantine.properties["lifecycle_status"] == "quarantined"
    assert (
        composite_quarantine.properties["replay_contract"]
        == "excluded_from_exact_replay"
    )

    tests_workflow = snapshot.nodes[NodeKey("workflow_surface", "tests")]
    assert tests_workflow.properties["workflow_family"] == "test"
    assert "pull_request" in tests_workflow.properties["trigger_names"]

    matrix_job = snapshot.nodes[NodeKey("workflow_job_surface", JOB_TEST_MATRIX)]
    assert matrix_job.properties["matrix_axes"] == ["python-version", "suite"]
    assert matrix_job.properties["matrix_variant_count"] >= 2

    secret_job = snapshot.nodes[NodeKey("workflow_job_surface", "docker::docker-push")]
    assert "GITHUB_TOKEN" in secret_job.properties["secret_usage_hints"]

    cli_command = snapshot.nodes[NodeKey("cli_command_surface", CMD_MEMORY_SYNC)]
    assert cli_command.properties["source_path"] == "scripts/memory/__main__.py"
    assert cli_command.properties["side_effect_class"] == "mutating"

    cli_option = next(
        node
        for node in snapshot.nodes.values()
        if node.key.label == "cli_option_surface"
    )
    assert cli_option.properties["option_name"] == "--pipeline"

    doc_claim = next(
        node
        for node in snapshot.nodes.values()
        if node.key.label == "doc_claim_surface"
    )
    assert doc_claim.properties["modality"] in {"required", "forbidden", "guidance"}
    assert isinstance(doc_claim.properties["claim_text"], str)
    assert doc_claim.properties["claim_text"]
    assert any(
        relation.source == doc_claim.key and relation.relation_type == "ASSERTS_ABOUT"
        for relation in snapshot.relations.values()
    )

    retry_state = snapshot.nodes[
        NodeKey("runtime_state_surface", STATE_MANIFEST_CHAIN_2)
    ]
    assert retry_state.properties["state_kind"] == "retry_state"
    assert retry_state.properties["state_status"] == "retrying"
    assert retry_state.properties["retry_count"] == 1

    lock_state = snapshot.nodes[
        NodeKey("runtime_state_surface", "chembl_activity::composite-lock")
    ]
    assert lock_state.properties["state_kind"] == "lock_state"
    assert lock_state.properties["lock_scope"] == "cross_validation_quarantine"
    assert lock_state.properties["lock_key"] == "composite:activity:cross_validation"

    assay_version_field = snapshot.nodes[
        NodeKey("schema_field_surface", "gold/chembl/assay::_version")
    ]
    assert assay_version_field.properties["field_name"] == "_version"
    assert assay_version_field.properties["drift_classification"] == "gold_only"

    activity_field = snapshot.nodes[
        NodeKey("schema_field_surface", SILVER_CHEMBL_ACTIVITY_FIELD)
    ]
    assert activity_field.properties["required_in_quality"] is True
    assert activity_field.properties["contract_ref"] == CONTRACT_CHEMBL_ACTIVITY
    assert activity_field.properties["drift_classification"] == "projected_to_gold"

    composite_field = snapshot.nodes[
        NodeKey("schema_field_surface", SILVER_COMPOSITE_ACTIVITY_FIELD)
    ]
    assert composite_field.properties["drift_classification"] == "inherited_field"
    assert (
        "silver/chembl/compound_record"
        in composite_field.properties["source_storage_refs"]
    )

    docs_drift_relation = snapshot.relations[
        (
            NodeKey("doc_artifact", RUN_MANIFEST_LEDGER_DOC_PATH),
            "DESCRIBES",
            NodeKey("module_surface", RUN_MANIFEST_MODULE_PATH),
        )
    ]
    assert docs_drift_relation.properties["doc_reference"] == RUN_MANIFEST_MODULE_PATH
    assert docs_drift_relation.properties["evidence_kind"] == "direct_path"
    assert docs_drift_relation.properties["confidence"] == "high"
    assert isinstance(docs_drift_relation.properties["line_number"], int)
    assert docs_drift_relation.properties["line_number"] > 0
    assert isinstance(docs_drift_relation.properties["section_title"], str)
    assert docs_drift_relation.properties["section_title"]


