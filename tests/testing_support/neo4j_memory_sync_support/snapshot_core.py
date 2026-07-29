# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Core snapshot surface assertions for Neo4j memory sync."""

# Names in this assertion module intentionally come from the shared test namespace.
# ruff: noqa: F405

from __future__ import annotations

from .common import *  # noqa: F403


def _assert_node_keys_present(
    node_keys: set[tuple[str, str]],
    expected: tuple[tuple[str, str], ...],
) -> None:
    for node_key in expected:
        assert node_key in node_keys


def _assert_node_keys_absent(
    node_keys: set[tuple[str, str]],
    forbidden: tuple[tuple[str, str], ...],
) -> None:
    for node_key in forbidden:
        assert node_key not in node_keys


def _assert_core_node_surfaces(
    node_keys: set[tuple[str, str]],
    snapshot: GraphSnapshot,
) -> None:
    _assert_node_keys_present(
        node_keys,
        (
            ("project", "BioETL"),
            ("repo_zone", "src"),
            ("repo_zone", "docs"),
            ("repo_zone", REPO_ZONE_GITHUB),
            ("directory_surface", APPLICATION_CORE_DIR),
            ("directory_surface", CHEMBL_CONFIG_DIR),
            ("directory_surface", TESTS_ARCHITECTURE_DIR),
            ("directory_surface", ARCHITECTURE_DIAGRAMS_DIR),
            ("directory_surface", SCRIPTS_OPS_DIR),
            ("directory_surface", GRAFANA_DASHBOARDS_DIR),
            ("directory_surface", GITHUB_WORKFLOWS_DIR),
            ("file_surface", RECORD_NORMALIZATION_PROCESSOR_PATH),
            ("file_surface", CHEMBL_ACTIVITY_CONFIG_PATH),
            ("file_surface", ARCHITECTURE_DIAGRAMS_README_PATH),
            ("file_surface", SCRIPTS_MEMORY_MAIN_PATH),
            ("file_surface", DIAGRAM_QUALITY_GATES_TEST_PATH),
            ("file_surface", BIOETL_RUNTIME_DASHBOARD_PATH),
            ("file_surface", TESTS_WORKFLOW_PATH),
            ("layer_family", "domain"),
            ("package_family", "domain/ports"),
            ("module_surface", "src/bioetl/domain/config/pipeline.py"),
            (
                "class_surface",
                "src.bioetl.infrastructure.adapters.base.BaseHttpAdapter",
            ),
            (
                "function_surface",
                "src.bioetl.domain.normalization.profiles.chembl_activity.create_case_normalizer",
            ),
            (
                "method_surface",
                "src.bioetl.application.composite.merge_service.MergeService.merge",
            ),
            ("provider_surface", "chembl"),
            ("entity_config", "chembl_activity"),
            ("composite_config", "composite_activity"),
            ("dashboard_surface", "bioetl-overview-v2"),
            ("doc_source_surface", ARCHITECTURE_DIAGRAMS_HUB),
            ("doc_source_surface", "diagram governance workflow"),
            ("doc_source_surface", "normalization plan"),
            ("doc_source_surface", "pipeline normalization matrix"),
            ("policy_surface", INTEGRATION_VCR_POLICY),
            ("policy_surface", DIAGRAM_GOVERNANCE_POLICY),
            ("script_surface", "scripts/engineering/dev/run_pytest.sh"),
            ("script_surface", "scripts/diagrams/__main__.py"),
            ("script_surface", "scripts/docs/__main__.py"),
            ("script_surface", "scripts/schema/__main__.py"),
            ("script_surface", SCRIPTS_MEMORY_MAIN_PATH),
            ("script_surface", "scripts/engineering/qa/__main__.py"),
            ("port_surface", "bioetl.domain.ports"),
            ("port_surface", "bioetl.domain.ports.runtime.runner.RunnablePort"),
            ("adapter_surface", CHEMBL_ADAPTER_SURFACE),
            ("adapter_impl_surface", CHEMBL_ADAPTER_IMPL_SURFACE),
            ("pipeline_surface", "chembl_activity"),
            ("contract_surface", CONTRACT_CHEMBL_ACTIVITY),
            ("alert_surface", "BioETLPipelineRunFailed"),
            ("runtime_evidence_surface", "run_manifest"),
            ("runtime_evidence_surface", "run_ledger"),
            ("runtime_evidence_surface", "effective_config_artifact"),
            ("runtime_evidence_surface", "lineage"),
            ("control_plane_artifact_surface", ARTIFACT_RUN_MANIFEST),
            ("control_plane_artifact_surface", ARTIFACT_EFFECTIVE_CONFIG),
            ("control_plane_artifact_surface", ARTIFACT_LINEAGE),
            ("workflow_surface", "tests"),
            ("workflow_job_surface", JOB_GOVERNANCE_PREFLIGHT),
            ("workflow_action_surface", ACTION_UPLOAD_ARTIFACT),
            ("workflow_action_surface", "./.github/actions/setup-python-uv"),
            ("workflow_artifact_surface", ARTIFACT_COVERAGE_DATA),
            ("workflow_secret_surface", "GITHUB_TOKEN"),
            ("cli_command_surface", CMD_BIOETL_RUN),
            ("cli_command_surface", CMD_MEMORY_SYNC),
            ("cli_command_surface", "scripts.docs verify"),
            ("execution_path", EXEC_BIOETL_RUN),
            ("execution_path", EXEC_DIAGRAMS_LINT),
            ("execution_path", EXEC_DOCS_VERIFY),
            ("execution_path", EXEC_SCHEMA_VALIDATE),
            (
                "execution_path",
                "uv run python -m scripts.docs generate-pipeline-normalization-matrix --check",
            ),
            (
                "execution_path",
                f"python -m scripts.memory sync --report {LEGACY_REPORT_PATH}",
            ),
            (
                "execution_path",
                "python -m scripts.engineering.qa report-normalization-fallback-inventory --limit 20",
            ),
            ("quality_gate", QUALITY_GATE_DIAGRAMS),
            (
                "test_artifact",
                "tests/unit/scripts/ops/neo4j_memory_sync/test_snapshot_topology.py",
            ),
        ),
    )
    assert any(label == "retirement_candidate" for label, _ in node_keys)
    assert any(label == "complexity_candidate" for label, _ in node_keys)
    assert any(label == "workflow_call_surface" for label, _ in node_keys)
    assert any(label == "workflow_matrix_variant_surface" for label, _ in node_keys)
    assert any(label == "workflow_output_surface" for label, _ in node_keys)
    assert any(label == "cli_option_surface" for label, _ in node_keys)
    assert any(label == "doc_claim_surface" for label, _ in node_keys)
    assert any(label == "duplication_cluster" for label, _ in node_keys)
    assert any(
        node.properties.get("current_cycle_status") == "current_cycle"
        for node in snapshot.nodes.values()
        if node.key.label
        in {"module_surface", "class_surface", "function_surface", "method_surface"}
    )


def _assert_storage_runtime_surfaces(
    node_keys: set[tuple[str, str]], snapshot: GraphSnapshot
) -> None:
    _assert_node_keys_present(
        node_keys,
        (
            ("storage_surface", SILVER_CHEMBL_ACTIVITY),
            ("storage_surface", SILVER_COMPOSITE_ACTIVITY),
            ("storage_surface", RUN_MANIFEST_STORAGE_PATH),
            ("storage_surface", EFFECTIVE_CONFIG_STORAGE_PATH),
            ("storage_surface", LINEAGE_FRAGMENT_STORAGE_PATH),
            ("run_instance_surface", "manifest-left"),
            ("run_instance_surface", "manifest-chain-smoke"),
            ("run_instance_surface", "manifest-chain-2"),
            ("run_instance_surface", "manifest-composite-quarantine"),
            ("runtime_state_surface", "manifest-left::active-window"),
            ("runtime_state_surface", STATE_MANIFEST_CHAIN_2),
            ("runtime_state_surface", "chembl_activity::composite-lock"),
            ("schema_field_surface", SILVER_CHEMBL_ACTIVITY_FIELD),
            ("schema_field_surface", "gold/chembl/assay::_version"),
            ("schema_field_surface", SILVER_COMPOSITE_ACTIVITY_FIELD),
        ),
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


def _assert_workflow_cli_and_doc_surfaces(
    node_keys: set[tuple[str, str]],
    snapshot: GraphSnapshot,
) -> None:
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

    _assert_node_keys_absent(
        node_keys,
        (
            ("package_family", "composition/__pycache__"),
            ("package_family", "infrastructure/__pycache__"),
            ("package_family", "interfaces/__pycache__"),
            ("directory_surface", "docs/99-archive"),
            ("directory_surface", "docs/reports/generated"),
            ("directory_surface", "scripts/archive"),
            ("directory_surface", "docs/02-architecture/diagrams/views/svg"),
            ("package_family", "composition/control_plane_api.py"),
            ("package_family", "interfaces/test_cli_checkpoint_list.py"),
        ),
    )


def _assert_schema_and_relation_surfaces(snapshot: GraphSnapshot) -> None:
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
            NodeKey("doc_source_surface", RUN_MANIFEST_LEDGER_DOC_PATH),
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


def test_snapshot_contains_core_repo_surfaces() -> None:
    _, snapshot = _snapshot()
    node_keys = {(key.label, key.name) for key in snapshot.nodes}
    _assert_core_node_surfaces(node_keys, snapshot)
    _assert_storage_runtime_surfaces(node_keys, snapshot)
    _assert_workflow_cli_and_doc_surfaces(node_keys, snapshot)
    _assert_schema_and_relation_surfaces(snapshot)
