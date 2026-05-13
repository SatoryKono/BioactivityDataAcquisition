"""Support helpers for invariant-focused Neo4j memory sync test suites."""

from __future__ import annotations

import io
import tempfile
from datetime import date
from pathlib import Path
from urllib import error

import pytest
from scripts.memory.sync import (
    DEFAULT_INGEST_WAVE,
    DEFAULT_LEGACY_PRUNE_LABELS,
    DEFAULT_MANAGED_BY,
    GraphSnapshot,
    Neo4jHttpClient,
    NodeKey,
    _add_complexity_analysis_surfaces,
    _build_diff_entries,
    _critical_analysis_audit_issues,
    _delete_managed_wave_nodes_statement,
    _docs_drift_sources,
    _duplication_analysis_config,
    _ensure_targeted_apply_prerequisites,
    _family_for_path,
    _filtered_snapshot,
    _git_last_commit_age_days_bulk,
    _live_managed_node_counts,
    _live_managed_relation_counts,
    _load_memory_mapping,
    _memory_mapping_path,
    _merge_storage_layer_config,
    _missing_managed_anchor_keys,
    _node_statement,
    _normalization_evidence_statements,
    _normalize_docs_repo_reference,
    _prune_legacy_unmanaged_nodes_statement,
    _prune_stale_nodes_statement,
    _prune_stale_relations_statement,
    _relation_statement,
    _reset_managed_relations_statement,
    _storage_ref_from_output_path,
    _targeted_apply_external_anchor_keys,
    _targeted_apply_required_anchor_labels,
    _verify_expected_group_counts,
    _workflow_quality_gates,
    apply_normalization_evidence_only,
    build_audit_report,
    build_fast_analysis_audit_report,
    build_snapshot,
    derive_http_uri,
    main,
    resolve_neo4j_connection,
    snapshot_invariant_issues,
    sync_snapshot,
)

pytestmark = pytest.mark.memory
LEGACY_REPORT_PATH = str(Path(tempfile.gettempdir()) / "neo4j-memory-audit.json")


def _test_internal_http_uri(host: str, port: int) -> str:
    """Test-only helper for explicitly required unencrypted HTTP connections."""
    return f"http://{host}:{port}"  # NOSONAR # nosec B108


LOCALHOST_HTTP_URI = _test_internal_http_uri("localhost", 7474)
LOCALHOST_AUDIT_HTTP_URI = _test_internal_http_uri("localhost", 7475)
HOST_DOCKER_INTERNAL_HTTP_URI = _test_internal_http_uri("host.docker.internal", 7474)
HOST_DOCKER_INTERNAL_AUDIT_HTTP_URI = _test_internal_http_uri(
    "host.docker.internal", 7475
)
CHEMBL_ACTIVITY_CONFIG_PATH = "configs/entities/chembl/activity.yaml"
RUN_MANIFEST_LEDGER_DOC_PATH = "docs/04-reference/contracts/run-manifest-ledger.md"
RUN_MANIFEST_MODULE_PATH = "src/bioetl/domain/control_plane/run_manifest.py"
APPLICATION_CORE_DIR = "src/bioetl/application/core"
CHEMBL_CONFIG_DIR = "configs/entities/chembl"
TESTS_ARCHITECTURE_DIR = "tests/architecture"
ARCHITECTURE_DIAGRAMS_DIR = "docs/02-architecture/diagrams"
SCRIPTS_OPS_DIR = "scripts/ops"
GRAFANA_DASHBOARDS_DIR = "grafana/dashboards"
GITHUB_WORKFLOWS_DIR = ".github/workflows"
RECORD_NORMALIZATION_PROCESSOR_PATH = (
    "src/bioetl/application/core/record_normalization_processor.py"
)
ARCHITECTURE_DIAGRAMS_README_PATH = "docs/02-architecture/diagrams/README.md"
SCRIPTS_MEMORY_MAIN_PATH = "scripts/memory/__main__.py"
DIAGRAM_QUALITY_GATES_TEST_PATH = "tests/architecture/test_diagram_quality_gates.py"
BIOETL_RUNTIME_DASHBOARD_PATH = "grafana/dashboards/bioetl-runtime.json"
TESTS_WORKFLOW_PATH = ".github/workflows/tests.yml"
SILVER_CHEMBL_ACTIVITY = "silver/chembl/activity"
SILVER_CHEMBL_ACTIVITY_FIELD = "silver/chembl/activity::activity_id"
SILVER_COMPOSITE_ACTIVITY = "silver/composite/activity"
SILVER_COMPOSITE_ACTIVITY_FIELD = "silver/composite/activity::compound_name"
RUN_MANIFEST_STORAGE_PATH = "control/run_manifest/{manifest_id}.json"
EFFECTIVE_CONFIG_STORAGE_PATH = "control/effective_config/{artifact_id}.json"
LINEAGE_FRAGMENT_STORAGE_PATH = "control/lineage/fragments/{fragment_hash}.json"
ARCHITECTURE_DIAGRAMS_HUB = "architecture diagrams hub"
INTEGRATION_VCR_POLICY = "integration and VCR execution policy"
DIAGRAM_GOVERNANCE_POLICY = "diagram governance policy"
CHEMBL_ADAPTER_SURFACE = "bioetl.infrastructure.adapters.chembl"
CHEMBL_ADAPTER_IMPL_SURFACE = "bioetl.infrastructure.adapters.chembl.client"


REPO_ZONE_GITHUB = ".github"
CONTRACT_CHEMBL_ACTIVITY = "chembl.activity"
ARTIFACT_RUN_MANIFEST = "run_manifest::json"
ARTIFACT_EFFECTIVE_CONFIG = "effective_config_artifact::json"
ARTIFACT_LINEAGE = "lineage::fragment"
STATE_MANIFEST_CHAIN_2 = "manifest-chain-2::retry-window"
JOB_GOVERNANCE_PREFLIGHT = "tests::governance-preflight"
ACTION_UPLOAD_ARTIFACT = "actions/upload-artifact"
ARTIFACT_COVERAGE_DATA = "tests::coverage-data-${{ matrix.test-group.name }}"
CMD_BIOETL_RUN = "bioetl run"
CMD_MEMORY_SYNC = "scripts.memory sync"
EXEC_BIOETL_RUN = "uv run python -m bioetl run --pipeline"
EXEC_DIAGRAMS_LINT = "uv run python -m scripts.diagrams lint"
EXEC_DOCS_VERIFY = "uv run python -m scripts.docs verify"
EXEC_SCHEMA_VALIDATE = "uv run python -m scripts.schema validate-configs"
QUALITY_GATE_DIAGRAMS = "diagram quality gates"
JOB_TEST_MATRIX = "tests::test-matrix"
PATH_CHEMBL_ACTIVITY_PROFILE = (
    "src/bioetl/domain/normalization/profiles/chembl_activity.py"
)
GATE_CONFIG_VALIDATION = "config validation"
ARTIFACT_RUN_LEDGER = "run_ledger::jsonl"
STMT_RETURN_1 = "RETURN 1 AS ok"
NEO4J_HTTP_CLIENT_PATH = "scripts.memory.sync.Neo4jHttpClient"
PATH_COMPOSITE_EXAMPLE = "src/bioetl/application/composite/example.py"
CLASS_PKG_EXAMPLE = "pkg.Example"
COMPLEXITY_PKG_EXAMPLE = "class_surface:pkg.Example"
CONTEXT_COMPLEXITY_PREREQ = (
    "complexity-layer targeted sync prerequisite anchor node check"
)
PATH_PKG_EXAMPLE = "src/pkg/example.py"
CONTEXT_FAST_AUDIT_LABEL = "fast audit label summary"
PATH_SRC_A = "src/a.py"
PATH_SRC_B = "src/b.py"
PATH_SRC_C = "src/c.py"
FAMILY_APP_COMPOSITE = "application/composite"


class _TargetedApplyPrereqStubClient:
    def query(
        self,
        _statement: str,
        parameters: dict[str, object] | None = None,
        *,
        context: str | None = None,
    ) -> list[dict[str, object]]:
        assert parameters is not None
        if context == "complexity-layer targeted sync prerequisite anchor check":
            labels = parameters["labels"]
            assert isinstance(labels, list)
            return [{"label": label, "count": 0} for label in labels]
        if context == CONTEXT_COMPLEXITY_PREREQ:
            anchors = parameters["anchors"]
            assert isinstance(anchors, list)
            return [
                {
                    "label": anchor["label"],
                    "name": anchor["name"],
                    "count": 0,
                }
                for anchor in anchors
            ]
        raise AssertionError(f"Unexpected context: {context}")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _snapshot() -> tuple[Path, object]:
    root = _repo_root()
    return root, build_snapshot(root, verified_at="2026-04-09")


def test_memory_mapping_path_prefers_canonical_graph_mapping(tmp_path: Path) -> None:
    canonical = tmp_path / "src/memory/graph"
    canonical.mkdir(parents=True)
    (canonical / "mappings.yaml").write_text("version: '1.0.0'\n", encoding="utf-8")
    legacy = tmp_path / "configs/quality"
    legacy.mkdir(parents=True)
    (legacy / "neo4j_memory_mapping.yaml").write_text(
        "version: '0.9.0'\n", encoding="utf-8"
    )

    assert _memory_mapping_path(tmp_path) == canonical / "mappings.yaml"


def test_derive_http_uri_from_bolt() -> None:
    assert derive_http_uri("bolt://localhost:7687") == LOCALHOST_HTTP_URI
    assert (
        derive_http_uri("neo4j+s://graph.example.com:7687")
        == "https://graph.example.com:7474"
    )


def test_resolve_neo4j_connection_uses_audit_instance_when_live_audit_mode_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LIVE_AUDIT_MODE", "1")
    monkeypatch.delenv("WSL_INTEROP", raising=False)
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_HTTP_URI", raising=False)
    monkeypatch.delenv("NEO4J_USERNAME", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.delenv("NEO4J_AUTH", raising=False)

    http_uri, username, password, database = resolve_neo4j_connection(tmp_path, None)

    assert http_uri == LOCALHOST_AUDIT_HTTP_URI
    assert username == "neo4j"
    assert password == "audit_secure_password"
    assert database == "neo4j"


def test_resolve_neo4j_connection_prefers_host_docker_internal_for_wsl_audit_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LIVE_AUDIT_MODE", "1")
    monkeypatch.setenv("WSL_INTEROP", "/run/WSL/123_interop")
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_HTTP_URI", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_URI", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_HTTP_URI", raising=False)

    http_uri, username, password, database = resolve_neo4j_connection(tmp_path, None)

    assert http_uri == HOST_DOCKER_INTERNAL_AUDIT_HTTP_URI
    assert username == "neo4j"
    assert password == "audit_secure_password"
    assert database == "neo4j"


def test_resolve_neo4j_connection_does_not_leak_default_mcp_credentials_into_audit_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LIVE_AUDIT_MODE", "1")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "bioetl_secure_password")
    monkeypatch.setenv("NEO4J_AUTH", "neo4j/bioetl_secure_password")
    monkeypatch.delenv("NEO4J_AUDIT_USERNAME", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_PASSWORD", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_AUTH", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_URI", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_HTTP_URI", raising=False)
    monkeypatch.delenv("WSL_INTEROP", raising=False)
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)

    http_uri, username, password, database = resolve_neo4j_connection(tmp_path, None)

    assert http_uri == LOCALHOST_AUDIT_HTTP_URI
    assert username == "neo4j"
    assert password == "audit_secure_password"
    assert database == "neo4j"


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


RelationKey = tuple[str, str, str, str, str]

EXPECTED_RELATION_KEYS: tuple[RelationKey, ...] = (
    ("project", "BioETL", "HAS_REPO_ZONE", "repo_zone", "src"),
    ("repo_zone", "src", "CONTAINS", "directory_surface", "src"),
    ("directory_surface", "src/bioetl/domain", "HOUSES", "layer_family", "domain"),
    (
        "directory_surface",
        "src/bioetl/domain/config",
        "HOUSES",
        "package_family",
        "domain/config",
    ),
    (
        "directory_surface",
        APPLICATION_CORE_DIR,
        "HOUSES",
        "module_surface",
        RECORD_NORMALIZATION_PROCESSOR_PATH,
    ),
    (
        "directory_surface",
        APPLICATION_CORE_DIR,
        "CONTAINS",
        "file_surface",
        RECORD_NORMALIZATION_PROCESSOR_PATH,
    ),
    (
        "file_surface",
        RECORD_NORMALIZATION_PROCESSOR_PATH,
        "BACKS",
        "module_surface",
        RECORD_NORMALIZATION_PROCESSOR_PATH,
    ),
    (
        "directory_surface",
        CHEMBL_CONFIG_DIR,
        "CONTAINS",
        "file_surface",
        CHEMBL_ACTIVITY_CONFIG_PATH,
    ),
    (
        "directory_surface",
        CHEMBL_CONFIG_DIR,
        "HOUSES",
        "entity_config",
        "chembl_activity",
    ),
    (
        "file_surface",
        CHEMBL_ACTIVITY_CONFIG_PATH,
        "BACKS",
        "entity_config",
        "chembl_activity",
    ),
    (
        "directory_surface",
        ARCHITECTURE_DIAGRAMS_DIR,
        "CONTAINS",
        "file_surface",
        ARCHITECTURE_DIAGRAMS_README_PATH,
    ),
    (
        "directory_surface",
        ARCHITECTURE_DIAGRAMS_DIR,
        "HOUSES",
        "doc_source_surface",
        ARCHITECTURE_DIAGRAMS_HUB,
    ),
    (
        "file_surface",
        ARCHITECTURE_DIAGRAMS_README_PATH,
        "BACKS",
        "doc_artifact",
        ARCHITECTURE_DIAGRAMS_README_PATH,
    ),
    (
        "directory_surface",
        "docs/03-guides",
        "HOUSES",
        "doc_source_surface",
        "testing guide",
    ),
    (
        "directory_surface",
        "docs/03-guides/dashboards",
        "HOUSES",
        "doc_source_surface",
        "dashboard extension guide",
    ),
    (
        "directory_surface",
        "docs/04-reference/contracts",
        "HOUSES",
        "doc_artifact",
        RUN_MANIFEST_LEDGER_DOC_PATH,
    ),
    (
        "directory_surface",
        "docs/05-operations/runbooks",
        "HOUSES",
        "doc_artifact",
        "docs/05-operations/runbooks/traceability-signal-ownership.md",
    ),
    (
        "directory_surface",
        SCRIPTS_OPS_DIR,
        "CONTAINS",
        "file_surface",
        SCRIPTS_MEMORY_MAIN_PATH,
    ),
    (
        "directory_surface",
        SCRIPTS_OPS_DIR,
        "HOUSES",
        "script_surface",
        SCRIPTS_MEMORY_MAIN_PATH,
    ),
    (
        "file_surface",
        SCRIPTS_MEMORY_MAIN_PATH,
        "BACKS",
        "script_surface",
        SCRIPTS_MEMORY_MAIN_PATH,
    ),
    (
        "directory_surface",
        TESTS_ARCHITECTURE_DIR,
        "CONTAINS",
        "file_surface",
        DIAGRAM_QUALITY_GATES_TEST_PATH,
    ),
    (
        "directory_surface",
        TESTS_ARCHITECTURE_DIR,
        "HOUSES",
        "test_surface",
        "architecture tests",
    ),
    (
        "directory_surface",
        TESTS_ARCHITECTURE_DIR,
        "HOUSES",
        "test_artifact",
        DIAGRAM_QUALITY_GATES_TEST_PATH,
    ),
    (
        "file_surface",
        DIAGRAM_QUALITY_GATES_TEST_PATH,
        "BACKS",
        "test_artifact",
        DIAGRAM_QUALITY_GATES_TEST_PATH,
    ),
    (
        "directory_surface",
        GRAFANA_DASHBOARDS_DIR,
        "CONTAINS",
        "file_surface",
        BIOETL_RUNTIME_DASHBOARD_PATH,
    ),
    (
        "directory_surface",
        GRAFANA_DASHBOARDS_DIR,
        "HOUSES",
        "dashboard_surface",
        "bioetl-runtime",
    ),
    (
        "file_surface",
        BIOETL_RUNTIME_DASHBOARD_PATH,
        "BACKS",
        "dashboard_surface",
        "bioetl-runtime",
    ),
    ("repo_zone", REPO_ZONE_GITHUB, "CONTAINS", "directory_surface", REPO_ZONE_GITHUB),
    (
        "directory_surface",
        GITHUB_WORKFLOWS_DIR,
        "CONTAINS",
        "file_surface",
        TESTS_WORKFLOW_PATH,
    ),
    ("directory_surface", GITHUB_WORKFLOWS_DIR, "HOUSES", "workflow_surface", "tests"),
    (
        "file_surface",
        TESTS_WORKFLOW_PATH,
        "BACKS",
        "workflow_surface",
        "tests",
    ),
    (
        "directory_surface",
        "configs/contracts",
        "HOUSES",
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
    ),
    (
        "directory_surface",
        "configs/contracts/chembl",
        "HOUSES",
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
    ),
    (
        "directory_surface",
        "configs/quality",
        "HOUSES",
        "policy_surface",
        INTEGRATION_VCR_POLICY,
    ),
    (
        "module_surface",
        "src/bioetl/infrastructure/adapters/base.py",
        "DECLARES",
        "class_surface",
        "src.bioetl.infrastructure.adapters.base.BaseHttpAdapter",
    ),
    (
        "module_surface",
        PATH_CHEMBL_ACTIVITY_PROFILE,
        "DECLARES",
        "function_surface",
        "src.bioetl.domain.normalization.profiles.chembl_activity.create_case_normalizer",
    ),
    (
        "class_surface",
        "src.bioetl.application.composite.merger.MergeService",
        "DECLARES",
        "method_surface",
        "src.bioetl.application.composite.merger.MergeService.merge",
    ),
    ("project", "BioETL", "HAS_PORT", "port_surface", "bioetl.domain.ports"),
    (
        "project",
        "BioETL",
        "HAS_ADAPTER",
        "adapter_surface",
        CHEMBL_ADAPTER_SURFACE,
    ),
    ("project", "BioETL", "HAS_PIPELINE", "pipeline_surface", "chembl_activity"),
    ("project", "BioETL", "HAS_CONTRACT", "contract_surface", CONTRACT_CHEMBL_ACTIVITY),
    ("project", "BioETL", "HAS_ALERT", "alert_surface", "BioETLPipelineRunFailed"),
    ("project", "BioETL", "HAS_PROVIDER", "provider_surface", "chembl"),
    ("provider_surface", "chembl", "DEFINES", "entity_config", "chembl_activity"),
    (
        "composite_config",
        "composite_activity",
        "DEPENDS_ON",
        "entity_config",
        "chembl_activity",
    ),
    (
        "project",
        "BioETL",
        "HAS_STORAGE_SURFACE",
        "storage_surface",
        SILVER_CHEMBL_ACTIVITY,
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "WRITES_TO",
        "storage_surface",
        SILVER_CHEMBL_ACTIVITY,
    ),
    (
        "pipeline_surface",
        "composite_activity",
        "DEPENDS_ON",
        "storage_surface",
        SILVER_CHEMBL_ACTIVITY,
    ),
    (
        "pipeline_surface",
        "composite_activity",
        "WRITES_TO",
        "storage_surface",
        SILVER_COMPOSITE_ACTIVITY,
    ),
    (
        "storage_surface",
        SILVER_COMPOSITE_ACTIVITY,
        "PROMOTES_TO",
        "storage_surface",
        "gold/composite/activity",
    ),
    (
        "package_family",
        "domain/config",
        "CONTAINS",
        "module_surface",
        "src/bioetl/domain/config/pipeline.py",
    ),
    (
        "project",
        "BioETL",
        "HAS_DOC_SOURCE_SURFACE",
        "doc_source_surface",
        ARCHITECTURE_DIAGRAMS_HUB,
    ),
    (
        "policy_surface",
        DIAGRAM_GOVERNANCE_POLICY,
        "GOVERNS",
        "quality_gate",
        QUALITY_GATE_DIAGRAMS,
    ),
    (
        "policy_surface",
        DIAGRAM_GOVERNANCE_POLICY,
        "GOVERNS",
        "test_surface",
        "architecture tests",
    ),
    (
        "policy_surface",
        DIAGRAM_GOVERNANCE_POLICY,
        "GOVERNS",
        "doc_source_surface",
        "diagram governance workflow",
    ),
    (
        "project",
        "BioETL",
        "HAS_POLICY_SURFACE",
        "policy_surface",
        INTEGRATION_VCR_POLICY,
    ),
    (
        "script_surface",
        "scripts/diagrams/__main__.py",
        "PROVIDES",
        "execution_path",
        EXEC_DIAGRAMS_LINT,
    ),
    (
        "execution_path",
        EXEC_DIAGRAMS_LINT,
        "EXECUTES_GATE",
        "quality_gate",
        QUALITY_GATE_DIAGRAMS,
    ),
    (
        "script_surface",
        "scripts/docs/__main__.py",
        "PROVIDES",
        "execution_path",
        EXEC_DOCS_VERIFY,
    ),
    (
        "execution_path",
        EXEC_DOCS_VERIFY,
        "EXECUTES_GATE",
        "quality_gate",
        "docs verification",
    ),
    (
        "script_surface",
        "scripts/schema/__main__.py",
        "PROVIDES",
        "execution_path",
        EXEC_SCHEMA_VALIDATE,
    ),
    (
        "execution_path",
        EXEC_SCHEMA_VALIDATE,
        "EXECUTES_GATE",
        "quality_gate",
        GATE_CONFIG_VALIDATION,
    ),
    (
        "script_surface",
        SCRIPTS_MEMORY_MAIN_PATH,
        "PROVIDES",
        "execution_path",
        f"python -m scripts.memory sync --report {LEGACY_REPORT_PATH}",
    ),
    (
        "policy_surface",
        INTEGRATION_VCR_POLICY,
        "GOVERNS",
        "test_surface",
        "integration tests",
    ),
    (
        "adapter_surface",
        CHEMBL_ADAPTER_SURFACE,
        "CONTAINS",
        "adapter_impl_surface",
        CHEMBL_ADAPTER_IMPL_SURFACE,
    ),
    (
        "adapter_impl_surface",
        CHEMBL_ADAPTER_IMPL_SURFACE,
        "DEPENDS_ON",
        "port_surface",
        "bioetl.domain.ports.observability.logging.LoggerPort",
    ),
    (
        "adapter_surface",
        CHEMBL_ADAPTER_SURFACE,
        "DEPENDS_ON",
        "port_surface",
        "bioetl.domain.ports.observability.logging.LoggerPort",
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "DEPENDS_ON",
        "adapter_surface",
        CHEMBL_ADAPTER_SURFACE,
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "DEPENDS_ON",
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "DEPENDS_ON",
        "module_surface",
        RECORD_NORMALIZATION_PROCESSOR_PATH,
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/domain/normalization/profiles/_chembl_activity_fields.py",
    ),
    (
        "entity_config",
        "chembl_activity",
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/domain/normalization/chembl.py",
    ),
    (
        "pipeline_surface",
        "crossref_publication",
        "DEPENDS_ON",
        "module_surface",
        RECORD_NORMALIZATION_PROCESSOR_PATH,
    ),
    (
        "entity_config",
        "crossref_publication",
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/domain/normalization/text.py",
    ),
    (
        "pipeline_surface",
        "composite_activity",
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/application/composite/join_key_normalization.py",
    ),
    (
        "contract_surface",
        "pubmed.publication",
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/domain/contracts/gold/_publication_common_schema.py",
    ),
    (
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
        "BACKED_BY",
        "config_artifact",
        "configs/contracts/chembl/activity.yaml",
    ),
    (
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
        "DESCRIBED_IN",
        "doc_artifact",
        RUN_MANIFEST_LEDGER_DOC_PATH,
    ),
    (
        "module_surface",
        RUN_MANIFEST_MODULE_PATH,
        "DESCRIBED_IN",
        "doc_artifact",
        RUN_MANIFEST_LEDGER_DOC_PATH,
    ),
    (
        "decision",
        "ADR-018-gold-strict-validation",
        "CONSTRAINS",
        "config_artifact",
        CHEMBL_ACTIVITY_CONFIG_PATH,
    ),
    (
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/application/services/control_plane/run_manifest_service.py",
    ),
    (
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/infrastructure/control_plane/file_effective_config_artifact_store.py",
    ),
    (
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/interfaces/cli/commands/run_manifest.py",
    ),
    (
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/application/services/lineage/lineage_inspection_service.py",
    ),
    (
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/composition/bootstrap/cli/lineage.py",
    ),
    (
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
        "DESCRIBED_IN",
        "doc_artifact",
        "docs/05-operations/runbooks/traceability-signal-ownership.md",
    ),
    (
        "policy_surface",
        "pipeline assembly model",
        "GOVERNS",
        "pipeline_surface",
        "chembl_activity",
    ),
    (
        "policy_surface",
        "observability surface model",
        "GOVERNS",
        "alert_surface",
        "BioETLPipelineRunFailed",
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "DEFINED_BY",
        "config_artifact",
        CHEMBL_ACTIVITY_CONFIG_PATH,
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "DESCRIBED_IN",
        "doc_artifact",
        "docs/04-reference/pipelines/chembl/05-activity-spec.md",
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "RUNS_VIA",
        "execution_path",
        EXEC_BIOETL_RUN,
    ),
    ("pipeline_surface", "chembl_activity", "VALIDATED_BY", "quality_gate", "pytest"),
    (
        "pipeline_surface",
        "chembl_activity",
        "VALIDATED_BY",
        "quality_gate",
        GATE_CONFIG_VALIDATION,
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "OBSERVED_BY",
        "dashboard_surface",
        "bioetl-dq-v2",
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "TESTED_BY",
        "test_artifact",
        "tests/integration/pipelines/test_chembl_activity.py",
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "TESTED_BY",
        "test_artifact",
        "tests/unit/infrastructure/adapters/chembl/test_request_metadata.py",
    ),
    (
        "pipeline_surface",
        "chembl_activity",
        "TESTED_BY",
        "test_surface",
        "integration tests",
    ),
    (
        "pipeline_surface",
        "composite_activity",
        "DEFINED_BY",
        "config_artifact",
        "configs/composites/activity.yaml",
    ),
    (
        "pipeline_surface",
        "composite_activity",
        "OBSERVED_BY",
        "dashboard_surface",
        "bioetl-control-plane-v1",
    ),
    (
        "alert_surface",
        "BioETLPipelineRunFailed",
        "DEPENDS_ON",
        "pipeline_surface",
        "chembl_activity",
    ),
    (
        "alert_surface",
        "BioETLPipelineRunFailed",
        "OBSERVED_BY",
        "dashboard_surface",
        "bioetl-runtime",
    ),
    (
        "alert_surface",
        "BioETLPipelineRunFailed",
        "DEPENDS_ON",
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
    ),
    (
        "alert_surface",
        "BioETLDQSoftThresholdExceeded",
        "DEPENDS_ON",
        "pipeline_surface",
        "chembl_activity",
    ),
    (
        "alert_surface",
        "BioETLProviderFailureRateHigh",
        "OBSERVED_BY",
        "dashboard_surface",
        "bioetl-provider-health-v2",
    ),
    (
        "alert_surface",
        "BioETLProviderFailureRateHigh",
        "DEPENDS_ON",
        "provider_surface",
        "chembl",
    ),
    (
        "alert_surface",
        "BioETLControlPlaneReadFailureRate",
        "OBSERVED_BY",
        "dashboard_surface",
        "bioetl-control-plane-v1",
    ),
    (
        "alert_surface",
        "BioETLControlPlaneReadFailureRate",
        "DEPENDS_ON",
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
    ),
    (
        "project",
        "BioETL",
        "HAS_RUNTIME_EVIDENCE",
        "runtime_evidence_surface",
        "run_manifest",
    ),
    (
        "runtime_evidence_surface",
        "run_manifest",
        "BACKED_BY",
        "module_surface",
        RUN_MANIFEST_MODULE_PATH,
    ),
    (
        "runtime_evidence_surface",
        "run_manifest",
        "WRITES_TO",
        "storage_surface",
        RUN_MANIFEST_STORAGE_PATH,
    ),
    (
        "project",
        "BioETL",
        "HAS_CONTROL_PLANE_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_RUN_MANIFEST,
    ),
    (
        "runtime_evidence_surface",
        "run_manifest",
        "EMITS_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_RUN_MANIFEST,
    ),
    (
        "control_plane_artifact_surface",
        ARTIFACT_RUN_MANIFEST,
        "MATERIALIZED_AS",
        "storage_surface",
        RUN_MANIFEST_STORAGE_PATH,
    ),
    (
        "runtime_evidence_surface",
        "effective_config_artifact",
        "WRITES_TO",
        "storage_surface",
        EFFECTIVE_CONFIG_STORAGE_PATH,
    ),
    (
        "runtime_evidence_surface",
        "effective_config_artifact",
        "EMITS_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_EFFECTIVE_CONFIG,
    ),
    (
        "control_plane_artifact_surface",
        ARTIFACT_EFFECTIVE_CONFIG,
        "MATERIALIZED_AS",
        "storage_surface",
        EFFECTIVE_CONFIG_STORAGE_PATH,
    ),
    (
        "runtime_evidence_surface",
        "lineage",
        "WRITES_TO",
        "storage_surface",
        LINEAGE_FRAGMENT_STORAGE_PATH,
    ),
    (
        "runtime_evidence_surface",
        "lineage",
        "EMITS_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_LINEAGE,
    ),
    (
        "control_plane_artifact_surface",
        ARTIFACT_LINEAGE,
        "MATERIALIZED_AS",
        "storage_surface",
        LINEAGE_FRAGMENT_STORAGE_PATH,
    ),
    ("project", "BioETL", "HAS_RUN_INSTANCE", "run_instance_surface", "manifest-left"),
    (
        "run_instance_surface",
        "manifest-left",
        "REFERENCES_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_RUN_MANIFEST,
    ),
    (
        "run_instance_surface",
        "manifest-left",
        "REFERENCES_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_EFFECTIVE_CONFIG,
    ),
    (
        "run_instance_surface",
        "manifest-chain-smoke",
        "REFERENCES_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_RUN_LEDGER,
    ),
    (
        "run_instance_surface",
        "manifest-chain-2",
        "DESCRIBED_IN",
        "test_artifact",
        "tests/unit/application/services/test_run_manifest_inspection_service.py",
    ),
    (
        "run_instance_surface",
        "manifest-composite-quarantine",
        "DEPENDS_ON",
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
    ),
    (
        "project",
        "BioETL",
        "HAS_RUNTIME_STATE",
        "runtime_state_surface",
        STATE_MANIFEST_CHAIN_2,
    ),
    (
        "run_instance_surface",
        "manifest-chain-2",
        "HAS_RUNTIME_STATE",
        "runtime_state_surface",
        STATE_MANIFEST_CHAIN_2,
    ),
    (
        "runtime_state_surface",
        STATE_MANIFEST_CHAIN_2,
        "DEPENDS_ON",
        "pipeline_surface",
        "chembl_activity",
    ),
    (
        "runtime_state_surface",
        STATE_MANIFEST_CHAIN_2,
        "REFERENCES_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_RUN_LEDGER,
    ),
    (
        "storage_surface",
        SILVER_CHEMBL_ACTIVITY,
        "HAS_SCHEMA_FIELD",
        "schema_field_surface",
        SILVER_CHEMBL_ACTIVITY_FIELD,
    ),
    (
        "contract_surface",
        CONTRACT_CHEMBL_ACTIVITY,
        "HAS_SCHEMA_FIELD",
        "schema_field_surface",
        SILVER_CHEMBL_ACTIVITY_FIELD,
    ),
    (
        "schema_field_surface",
        "silver/chembl/assay::assay_id",
        "PROMOTES_FIELD_TO",
        "schema_field_surface",
        "gold/chembl/assay::assay_id",
    ),
    (
        "schema_field_surface",
        SILVER_COMPOSITE_ACTIVITY_FIELD,
        "DERIVES_FIELD_FROM",
        "schema_field_surface",
        "silver/chembl/compound_record::compound_name",
    ),
    ("project", "BioETL", "HAS_WORKFLOW", "workflow_surface", "tests"),
    (
        "workflow_surface",
        "tests",
        "CONTAINS",
        "workflow_job_surface",
        JOB_GOVERNANCE_PREFLIGHT,
    ),
    (
        "workflow_job_surface",
        JOB_GOVERNANCE_PREFLIGHT,
        "EXECUTES_GATE",
        "quality_gate",
        "deterministic neo4j memory ontology invariants",
    ),
    (
        "workflow_job_surface",
        JOB_TEST_MATRIX,
        "USES_ACTION",
        "workflow_action_surface",
        ACTION_UPLOAD_ARTIFACT,
    ),
    (
        "workflow_job_surface",
        JOB_TEST_MATRIX,
        "PUBLISHES_ARTIFACT",
        "workflow_artifact_surface",
        ARTIFACT_COVERAGE_DATA,
    ),
    (
        "workflow_job_surface",
        "docker::docker-push",
        "REQUIRES_SECRET",
        "workflow_secret_surface",
        "GITHUB_TOKEN",
    ),
    ("project", "BioETL", "HAS_CLI_COMMAND", "cli_command_surface", CMD_BIOETL_RUN),
    (
        "cli_command_surface",
        CMD_BIOETL_RUN,
        "RUNS_VIA",
        "execution_path",
        EXEC_BIOETL_RUN,
    ),
    (
        "cli_command_surface",
        CMD_BIOETL_RUN,
        "SIDE_EFFECTS_ON",
        "pipeline_surface",
        "chembl_activity",
    ),
    (
        "cli_command_surface",
        CMD_MEMORY_SYNC,
        "RUNS_VIA",
        "execution_path",
        f"python -m scripts.memory sync --report {LEGACY_REPORT_PATH}",
    ),
    (
        "doc_artifact",
        RUN_MANIFEST_LEDGER_DOC_PATH,
        "DESCRIBES",
        "module_surface",
        RUN_MANIFEST_MODULE_PATH,
    ),
    (
        "doc_artifact",
        RUN_MANIFEST_LEDGER_DOC_PATH,
        "DESCRIBES",
        "module_surface",
        "src/bioetl/infrastructure/config/_base.py",
    ),
    (
        "doc_artifact",
        "scripts/engineering/dev/README.md",
        "DESCRIBES",
        "execution_path",
        "bash scripts/engineering/dev/run_pytest.sh",
    ),
    (
        "script_surface",
        "scripts/engineering/dev/run_pytest.sh",
        "PROVIDES",
        "execution_path",
        "bash scripts/engineering/dev/run_pytest.sh",
    ),
    (
        "layer_family",
        "composition",
        "CONTAINS",
        "module_surface",
        "src/bioetl/composition/control_plane_api.py",
    ),
)

FORBIDDEN_RELATION_KEYS: tuple[RelationKey, ...] = (
    ("repo_zone", "docs", "CONTAINS", "directory_surface", "docs/99-archive"),
    (
        "pipeline_surface",
        "composite_activity",
        "OBSERVED_BY",
        "dashboard_surface",
        "bioetl-silver-reject-explorer",
    ),
    (
        "alert_surface",
        "BioETLDQSoftThresholdExceeded",
        "DEPENDS_ON",
        "pipeline_surface",
        "composite_activity",
    ),
    (
        "test_artifact",
        "tests/unit/scripts/ops/neo4j_memory_sync/test_snapshot_topology.py",
        "TESTS_LAYER",
        "layer_family",
        "scripts",
    ),
    (
        "test_artifact",
        "tests/integration/interfaces/test_cli_checkpoint_list.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "interfaces/test_cli_checkpoint_list.py",
    ),
    (
        "test_artifact",
        "tests/unit/domain/configs/test_base_configs.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "domain/configs",
    ),
    (
        "test_artifact",
        "tests/unit/domain/hash_policy/test_hash_policy_stability.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "domain/hash_policy",
    ),
    (
        "test_artifact",
        "tests/unit/infrastructure/factories/test_factories.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "infrastructure/factories",
    ),
    (
        "test_artifact",
        "tests/unit/interfaces/factories/test_pipeline_factories.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "interfaces/factories",
    ),
)


def _relation_keys(snapshot: object) -> set[RelationKey]:
    return {
        (
            rel.source.label,
            rel.source.name,
            rel.relation_type,
            rel.target.label,
            rel.target.name,
        )
        for rel in snapshot.relations.values()
    }


def _assert_relation_membership(
    relation_keys: set[RelationKey], expected: tuple[RelationKey, ...]
) -> None:
    for relation_key in expected:
        assert relation_key in relation_keys


def test_normalization_evidence_statements_cover_registry_and_fallback_metrics() -> (
    None
):
    statements = _normalization_evidence_statements()
    chembl_activity = next(
        item
        for item in statements
        if item["parameters"]["pipeline_name"] == "chembl_activity"
    )
    assay_parameters = next(
        item
        for item in statements
        if item["parameters"]["pipeline_name"] == "chembl_assay_parameters"
    )

    chembl_params = chembl_activity["parameters"]
    assert chembl_params["normalization_profile_registered"] is True
    assert chembl_params["normalization_profile_module_path"] == (
        PATH_CHEMBL_ACTIVITY_PROFILE
    )
    assert chembl_params["profile_field_count"] > 0

    assay_params = assay_parameters["parameters"]
    assert assay_params["normalization_profile_registered"] is True
    assert assay_params["normalization_profile_module_path"] == (
        "src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py"
    )
    assert assay_params["profile_field_count"] > 0
    assert assay_params["fallback_business_field_count"] == 0
    assert assay_params["fallback_field_count"] == 0


def test_apply_normalization_evidence_only_executes_batched_statements(
    monkeypatch,
) -> None:
    executed_batches: list[list[dict[str, object]]] = []
    batch_contexts: list[str | None] = []
    stub_statements = [
        {
            "statement": STMT_RETURN_1,
            "parameters": {"pipeline_name": "chembl_activity"},
        },
        {
            "statement": STMT_RETURN_1,
            "parameters": {"pipeline_name": "pubmed_publication"},
        },
        {
            "statement": STMT_RETURN_1,
            "parameters": {"pipeline_name": "crossref_publication"},
        },
    ]

    class StubClient:
        def __init__(
            self, base_uri: str, username: str, password: str, database: str
        ) -> None:
            self.base_uri = base_uri
            self.username = username
            self.password = password
            self.database = database

        def execute(
            self,
            statements: list[dict[str, object]],
            *,
            context: str | None = None,
        ) -> dict[str, object]:
            executed_batches.append(statements)
            batch_contexts.append(context)
            return {"results": [], "errors": []}

    monkeypatch.setattr(NEO4J_HTTP_CLIENT_PATH, StubClient)
    monkeypatch.setattr(
        "scripts.memory.sync._normalization_evidence_statements",
        lambda: list(stub_statements),
    )
    root = _repo_root()

    summary = apply_normalization_evidence_only(
        root,
        HOST_DOCKER_INTERNAL_HTTP_URI,
        batch_size=2,
    )

    assert summary["pipeline_count"] == len(stub_statements)
    assert summary["completed_statement_count"] == len(stub_statements)
    assert summary["batch_count"] == len(executed_batches)
    assert summary["batch_size"] == 2
    assert len(summary["batches"]) == len(executed_batches)
    assert executed_batches
    assert sum(len(batch) for batch in executed_batches) == len(stub_statements)
    assert batch_contexts
    assert batch_contexts[0] is not None
    assert "normalization evidence batch 1/" in str(batch_contexts[0])
    assert summary["batches"][0]["pipeline_start"] == "chembl_activity"
    assert summary["batches"][0]["pipeline_end"] == "pubmed_publication"


def test_duplication_analysis_config_excludes_normalization_registry_path() -> None:
    root = _repo_root()
    config = _duplication_analysis_config(_load_memory_mapping(root))

    assert (
        _family_for_path(
            "src/bioetl/domain/normalization/profiles/registry.py",
            config,
        )
        is None
    )
    family = _family_for_path(
        "src/bioetl/domain/normalization/profiles/chembl_molecule.py",
        config,
    )
    assert family is not None
    assert family.name == "normalization_profiles"


def _assert_relation_absence(
    relation_keys: set[RelationKey], forbidden: tuple[RelationKey, ...]
) -> None:
    for relation_key in forbidden:
        assert relation_key not in relation_keys


def test_snapshot_contains_expected_relations() -> None:
    _, snapshot = _snapshot()
    relation_keys = _relation_keys(snapshot)

    _assert_relation_membership(relation_keys, EXPECTED_RELATION_KEYS)
    _assert_relation_absence(relation_keys, FORBIDDEN_RELATION_KEYS)


def test_snapshot_enriches_current_normalization_topology() -> None:
    _, snapshot = _snapshot()

    chembl_activity = snapshot.nodes[NodeKey("pipeline_surface", "chembl_activity")]
    assert chembl_activity.properties["normalization_profile_registered"] is True
    assert (
        chembl_activity.properties["normalization_profile_module_path"]
        == PATH_CHEMBL_ACTIVITY_PROFILE
    )
    assert int(chembl_activity.properties["profile_field_count"]) > 0

    assay_parameters = snapshot.nodes[
        NodeKey("pipeline_surface", "chembl_assay_parameters")
    ]
    assert assay_parameters.properties["normalization_profile_registered"] is True
    assert (
        assay_parameters.properties["normalization_profile_module_path"]
        == "src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py"
    )
    assert int(assay_parameters.properties["profile_field_count"]) > 0
    assert int(assay_parameters.properties["fallback_business_field_count"]) == 0
    assert int(assay_parameters.properties["fallback_field_count"]) == 0

    relation_keys = _relation_keys(snapshot)
    assert (
        "pipeline_surface",
        "crossref_publication",
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/domain/normalization/profiles/crossref_publication.py",
    ) in relation_keys
    assert (
        "entity_config",
        "crossref_publication",
        "DEPENDS_ON",
        "module_surface",
        "src/bioetl/domain/normalization/profiles/crossref_publication.py",
    ) in relation_keys


def test_snapshot_contains_duplication_clusters_with_promotion_targets() -> None:
    _, snapshot = _snapshot()

    duplication_clusters = [
        node
        for node in snapshot.nodes.values()
        if node.key.label == "duplication_cluster"
    ]
    assert duplication_clusters

    cluster_relations = {
        (rel.source.label, rel.relation_type, rel.target.label)
        for rel in snapshot.relations.values()
        if rel.source.label == "duplication_cluster"
    }
    assert (
        "duplication_cluster",
        "CONTAINS",
        "method_surface",
    ) in cluster_relations or (
        "duplication_cluster",
        "CONTAINS",
        "function_surface",
    ) in cluster_relations
    assert any(
        rel.source.label == "duplication_cluster"
        and rel.relation_type == "CAN_PROMOTE_TO"
        for rel in snapshot.relations.values()
    )
    assert any(
        rel.relation_type == "COVERED_BY_TEST"
        and rel.source.label == "duplication_cluster"
        for rel in snapshot.relations.values()
    )


def test_snapshot_excludes_normalization_registry_duplication_noise() -> None:
    _, snapshot = _snapshot()

    registry_members = [
        rel.target
        for rel in snapshot.relations.values()
        if rel.source.label == "duplication_cluster"
        and rel.relation_type == "CONTAINS"
        and rel.target.label in {"function_surface", "method_surface"}
        and "src.bioetl.domain.normalization.profiles.registry." in rel.target.name
    ]

    assert registry_members == []


def test_snapshot_contains_complexity_candidates_with_simplification_links() -> None:
    _, snapshot = _snapshot()

    complexity_candidates = [
        node
        for node in snapshot.nodes.values()
        if node.key.label == "complexity_candidate"
    ]
    assert complexity_candidates
    assert any(
        rel.source.label
        in {"module_surface", "class_surface", "function_surface", "method_surface"}
        and rel.relation_type == "HAS_COMPLEXITY_SIGNAL"
        and rel.target.label == "complexity_candidate"
        for rel in snapshot.relations.values()
    )
    assert any(
        rel.source.label == "complexity_candidate"
        and rel.relation_type == "CANDIDATE_FOR_SIMPLIFICATION"
        for rel in snapshot.relations.values()
    )


def test_sync_statements_include_management_metadata() -> None:
    _, snapshot = _snapshot()
    project_node = snapshot.nodes[
        next(
            key
            for key in snapshot.nodes
            if key.label == "project" and key.name == "BioETL"
        )
    ]
    relation = next(iter(snapshot.relations.values()))

    node_statement = _node_statement(project_node, "sync-run-1")
    relation_statement = _relation_statement(relation, "sync-run-1")

    node_properties = node_statement["parameters"]["properties"]
    relation_properties = relation_statement["parameters"]["properties"]

    assert node_properties["managed_by"] == DEFAULT_MANAGED_BY
    assert node_properties["ingest_wave"] == DEFAULT_INGEST_WAVE
    assert node_properties["sync_run"] == "sync-run-1"
    assert relation_properties["managed_by"] == DEFAULT_MANAGED_BY
    assert relation_properties["ingest_wave"] == DEFAULT_INGEST_WAVE
    assert relation_properties["sync_run"] == "sync-run-1"


def test_prune_statements_target_repo_sync_subgraph() -> None:
    reset_statement = _reset_managed_relations_statement(["CONTAINS", "DEFINED_BY"])
    prune_relations_statement = _prune_stale_relations_statement("sync-run-2")
    prune_nodes_statement = _prune_stale_nodes_statement("sync-run-2")
    full_reset_statement = _delete_managed_wave_nodes_statement("module_surface", 10)
    legacy_prune_statement = _prune_legacy_unmanaged_nodes_statement(
        ["quality_gate", "execution_path"]
    )

    assert "type(r) IN $relation_types" in reset_statement["statement"]
    assert reset_statement["parameters"]["relation_types"] == ["CONTAINS", "DEFINED_BY"]
    assert reset_statement["parameters"]["managed_by"] == DEFAULT_MANAGED_BY
    assert reset_statement["parameters"]["ingest_wave"] == DEFAULT_INGEST_WAVE

    assert (
        "coalesce(r.sync_run, '') <> $sync_run"
        in prune_relations_statement["statement"]
    )
    assert prune_relations_statement["parameters"]["managed_by"] == DEFAULT_MANAGED_BY
    assert prune_relations_statement["parameters"]["ingest_wave"] == DEFAULT_INGEST_WAVE
    assert prune_relations_statement["parameters"]["sync_run"] == "sync-run-2"

    assert "DETACH DELETE n" in prune_nodes_statement["statement"]
    assert prune_nodes_statement["parameters"]["ingest_wave"] == DEFAULT_INGEST_WAVE
    assert prune_nodes_statement["parameters"]["sync_run"] == "sync-run-2"

    assert "DETACH DELETE n" in full_reset_statement["statement"]
    assert full_reset_statement["parameters"]["ingest_wave"] == DEFAULT_INGEST_WAVE
    assert full_reset_statement["parameters"]["managed_by"] == DEFAULT_MANAGED_BY

    assert (
        "any(label IN labels(n) WHERE label IN $managed_labels)"
        in legacy_prune_statement["statement"]
    )
    assert "coalesce(n.managed_by, '') = ''" in legacy_prune_statement["statement"]
    assert legacy_prune_statement["parameters"]["managed_labels"] == [
        "quality_gate",
        "execution_path",
    ]


def test_default_legacy_prune_labels_cover_repo_managed_surfaces() -> None:
    expected_labels = {
        "project",
        "repo_zone",
        "directory_surface",
        "file_surface",
        "doc_source_surface",
        "doc_artifact",
        "decision",
        "risk",
        "policy_surface",
        "layer_family",
        "package_family",
        "module_surface",
        "class_surface",
        "function_surface",
        "method_surface",
        "duplication_cluster",
        "retirement_candidate",
        "complexity_candidate",
        "port_surface",
        "adapter_surface",
        "adapter_impl_surface",
        "pipeline_surface",
        "contract_surface",
        "alert_surface",
        "provider_surface",
        "entity_config",
        "composite_config",
        "config_artifact",
        "dashboard_surface",
        "quality_gate",
        "script_surface",
        "execution_path",
        "test_surface",
        "test_artifact",
        "storage_surface",
        "runtime_evidence_surface",
        "control_plane_artifact_surface",
        "run_instance_surface",
        "runtime_state_surface",
        "schema_field_surface",
        "workflow_surface",
        "workflow_job_surface",
        "workflow_call_surface",
        "workflow_matrix_variant_surface",
        "workflow_output_surface",
        "workflow_action_surface",
        "workflow_artifact_surface",
        "workflow_secret_surface",
        "cli_command_surface",
        "cli_option_surface",
        "doc_claim_surface",
    }

    assert set(DEFAULT_LEGACY_PRUNE_LABELS) == expected_labels


def test_build_diff_entries_tracks_missing_and_extra_keys() -> None:
    diff_entries = _build_diff_entries(
        {"policy_surface": 16, "package_family": 52},
        {"policy_surface": 16, "package_family": 50, "execution_path": 9},
    )

    assert diff_entries == [
        {
            "name": "execution_path",
            "snapshot": 0,
            "live_managed": 9,
            "delta": 9,
        },
        {
            "name": "package_family",
            "snapshot": 52,
            "live_managed": 50,
            "delta": -2,
        },
        {
            "name": "policy_surface",
            "snapshot": 16,
            "live_managed": 16,
            "delta": 0,
        },
    ]


def test_storage_surface_helpers_merge_base_and_pipeline_overrides() -> None:
    merged = _merge_storage_layer_config(
        {
            "silver": {
                "format": "delta",
                "mode": "merge",
                "enabled": True,
            }
        },
        {
            "silver": {
                "mode": "append",
            }
        },
        "silver",
    )

    assert merged == {
        "format": "delta",
        "mode": "append",
        "enabled": True,
    }


def test_storage_ref_from_output_path_normalizes_data_output_prefix() -> None:
    assert (
        _storage_ref_from_output_path(f"data/output/{SILVER_COMPOSITE_ACTIVITY}")
        == SILVER_COMPOSITE_ACTIVITY
    )
    assert (
        _storage_ref_from_output_path(SILVER_CHEMBL_ACTIVITY) == SILVER_CHEMBL_ACTIVITY
    )


def test_filtered_snapshot_storage_layer_preserves_storage_runtime_and_artifact_links() -> (
    None
):
    _, snapshot = _snapshot()

    filtered = _filtered_snapshot(snapshot, only_storage_layer=True)
    relation_keys = _relation_keys(filtered)

    assert ("storage_surface", SILVER_CHEMBL_ACTIVITY) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert ("control_plane_artifact_surface", ARTIFACT_RUN_MANIFEST) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert ("run_instance_surface", "manifest-chain-smoke") in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert ("runtime_state_surface", STATE_MANIFEST_CHAIN_2) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert ("schema_field_surface", SILVER_CHEMBL_ACTIVITY_FIELD) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert (
        "pipeline_surface",
        "chembl_activity",
        "WRITES_TO",
        "storage_surface",
        SILVER_CHEMBL_ACTIVITY,
    ) in relation_keys
    assert (
        "runtime_evidence_surface",
        "run_manifest",
        "EMITS_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_RUN_MANIFEST,
    ) in relation_keys
    assert (
        "run_instance_surface",
        "manifest-chain-smoke",
        "REFERENCES_ARTIFACT",
        "control_plane_artifact_surface",
        ARTIFACT_RUN_LEDGER,
    ) in relation_keys
    assert (
        "storage_surface",
        SILVER_CHEMBL_ACTIVITY,
        "HAS_SCHEMA_FIELD",
        "schema_field_surface",
        SILVER_CHEMBL_ACTIVITY_FIELD,
    ) in relation_keys


def test_filtered_snapshot_runtime_evidence_layer_preserves_runtime_support_links() -> (
    None
):
    _, snapshot = _snapshot()

    filtered = _filtered_snapshot(snapshot, only_runtime_evidence_layer=True)
    relation_keys = _relation_keys(filtered)

    assert ("runtime_evidence_surface", "run_manifest") in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert ("run_instance_surface", "manifest-chain-2") in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert ("runtime_state_surface", STATE_MANIFEST_CHAIN_2) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert ("module_surface", RUN_MANIFEST_MODULE_PATH) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert (
        "runtime_evidence_surface",
        "run_manifest",
        "BACKED_BY",
        "module_surface",
        RUN_MANIFEST_MODULE_PATH,
    ) in relation_keys
    assert (
        "run_instance_surface",
        "manifest-chain-2",
        "DESCRIBED_IN",
        "test_artifact",
        "tests/unit/application/services/test_run_manifest_inspection_service.py",
    ) in relation_keys
    assert (
        "run_instance_surface",
        "manifest-chain-2",
        "HAS_RUNTIME_STATE",
        "runtime_state_surface",
        STATE_MANIFEST_CHAIN_2,
    ) in relation_keys


def test_filtered_snapshot_workflow_graph_preserves_job_gate_and_run_targets() -> None:
    _, snapshot = _snapshot()

    filtered = _filtered_snapshot(snapshot, only_workflow_graph=True)
    relation_keys = _relation_keys(filtered)

    assert ("workflow_surface", "tests") in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert ("workflow_job_surface", JOB_GOVERNANCE_PREFLIGHT) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert any(key.label == "workflow_call_surface" for key in filtered.nodes)
    assert any(key.label == "workflow_matrix_variant_surface" for key in filtered.nodes)
    assert any(key.label == "workflow_output_surface" for key in filtered.nodes)
    assert ("workflow_action_surface", ACTION_UPLOAD_ARTIFACT) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert (
        "workflow_artifact_surface",
        ARTIFACT_COVERAGE_DATA,
    ) in {(key.label, key.name) for key in filtered.nodes}
    assert (
        "workflow_job_surface",
        JOB_GOVERNANCE_PREFLIGHT,
        "EXECUTES_GATE",
        "quality_gate",
        "pytest",
    ) in relation_keys
    assert (
        "workflow_job_surface",
        JOB_GOVERNANCE_PREFLIGHT,
        "RUNS_VIA",
        "script_surface",
        "scripts/engineering/qa/__main__.py",
    ) in relation_keys
    assert (
        "workflow_job_surface",
        JOB_TEST_MATRIX,
        "USES_ACTION",
        "workflow_action_surface",
        ACTION_UPLOAD_ARTIFACT,
    ) in relation_keys
    assert (
        "workflow_job_surface",
        JOB_TEST_MATRIX,
        "PUBLISHES_ARTIFACT",
        "workflow_artifact_surface",
        ARTIFACT_COVERAGE_DATA,
    ) in relation_keys
    assert any(
        relation_key[2] == "CALLS_WORKFLOW"
        and relation_key[3] == "workflow_call_surface"
        for relation_key in relation_keys
    )
    assert any(
        relation_key[2] == "HAS_MATRIX_VARIANT"
        and relation_key[3] == "workflow_matrix_variant_surface"
        for relation_key in relation_keys
    )
    assert any(
        relation_key[2] == "EMITS_OUTPUT"
        and relation_key[3] == "workflow_output_surface"
        for relation_key in relation_keys
    )


def test_filtered_snapshot_docs_drift_preserves_describes_edges() -> None:
    _, snapshot = _snapshot()

    filtered = _filtered_snapshot(snapshot, only_docs_drift=True)
    relation_keys = _relation_keys(filtered)
    chembl_doc_claims = {
        key.name
        for key in filtered.nodes
        if key.label == "doc_claim_surface"
        and key.name.startswith(
            "docs/04-reference/pipelines/chembl/05-activity-spec.md#L"
        )
    }

    assert ("doc_artifact", RUN_MANIFEST_LEDGER_DOC_PATH) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert (
        "doc_artifact",
        RUN_MANIFEST_LEDGER_DOC_PATH,
        "DESCRIBES",
        "module_surface",
        RUN_MANIFEST_MODULE_PATH,
    ) in relation_keys
    assert (
        "module_surface",
        RUN_MANIFEST_MODULE_PATH,
        "DESCRIBED_IN",
        "doc_artifact",
        RUN_MANIFEST_LEDGER_DOC_PATH,
    ) in relation_keys
    assert chembl_doc_claims
    assert any(
        (
            "doc_artifact",
            "docs/04-reference/pipelines/chembl/05-activity-spec.md",
            "ASSERTS",
            "doc_claim_surface",
            claim_name,
        )
        in relation_keys
        for claim_name in chembl_doc_claims
    )
    assert ("cli_command_surface", CMD_MEMORY_SYNC) in {
        (key.label, key.name) for key in filtered.nodes
    }


def test_snapshot_contains_workflow_execution_cli_and_claim_extensions() -> None:
    _, snapshot = _snapshot()

    relation_keys = _relation_keys(snapshot)

    assert any(key.label == "workflow_call_surface" for key in snapshot.nodes)
    assert any(key.label == "workflow_matrix_variant_surface" for key in snapshot.nodes)
    assert any(key.label == "workflow_output_surface" for key in snapshot.nodes)
    assert any(key.label == "cli_option_surface" for key in snapshot.nodes)
    assert any(key.label == "doc_claim_surface" for key in snapshot.nodes)

    assert any(
        relation_key[0] == "workflow_job_surface"
        and relation_key[2] == "CALLS_WORKFLOW"
        for relation_key in relation_keys
    )
    assert any(
        relation_key[0] == "workflow_job_surface"
        and relation_key[2] == "HAS_MATRIX_VARIANT"
        for relation_key in relation_keys
    )
    assert any(
        relation_key[2] == "EMITS_OUTPUT"
        and relation_key[3] == "workflow_output_surface"
        for relation_key in relation_keys
    )
    assert any(
        relation_key[0] == "cli_command_surface" and relation_key[2] == "ACCEPTS_OPTION"
        for relation_key in relation_keys
    )
    assert any(
        relation_key[0] == "doc_claim_surface" and relation_key[2] == "ASSERTS_ABOUT"
        for relation_key in relation_keys
    )


def test_workflow_quality_gates_detect_repo_gate_signals() -> None:
    gates = _workflow_quality_gates(
        "uv run python -m scripts.engineering.ci neo4j-memory\n"
        "uv run python -m scripts.schema validate-configs\n"
        "uv run pytest tests/smoke/\n"
    )

    assert gates == (
        "pytest",
        GATE_CONFIG_VALIDATION,
        "deterministic neo4j memory ontology invariants",
    )


def test_normalize_docs_repo_reference_strips_globs_and_keeps_repo_paths() -> None:
    assert (
        _normalize_docs_repo_reference("src/bioetl/domain/control_plane/**")
        == "src/bioetl/domain/control_plane"
    )
    assert (
        _normalize_docs_repo_reference("configs/providers/*.yaml")
        == "configs/providers"
    )
    assert _normalize_docs_repo_reference("README.md") == "README.md"
    assert _normalize_docs_repo_reference("https://example.com/spec") is None


def test_development_cycle_surface_filter_is_now_a_clean_noop() -> None:
    snapshot = GraphSnapshot()
    current_code = snapshot.add_node(
        "module_surface",
        PATH_COMPOSITE_EXAMPLE,
        current_cycle_status="current_cycle",
    )
    candidate = snapshot.add_node(
        "retirement_candidate",
        PATH_COMPOSITE_EXAMPLE,
        blocked_by_current_cycle=True,
    )
    snapshot.add_relation(current_code, "CANDIDATE_FOR_REMOVAL", candidate)

    filtered = _filtered_snapshot(snapshot, only_labels=("development_cycle_surface",))
    stats = filtered.stats()

    assert stats["node_count"] == 0
    assert stats["relation_count"] == 0
    assert stats["labels"] == {}
    assert stats["relation_types"] == {}


def test_docs_drift_sources_skips_unreadable_doc_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    relative_path = "docs/unreadable.md"
    doc_path = tmp_path / relative_path
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text("# placeholder\n", encoding="utf-8")

    snapshot = GraphSnapshot()
    doc_key = snapshot.add_node(
        "doc_artifact",
        relative_path,
        source_path=relative_path,
    )

    def _raise_read_error(path: Path) -> str:
        if path == doc_path:
            raise OSError("Invalid argument")
        return path.read_text(encoding="utf-8")

    monkeypatch.setattr("scripts.memory.sync._read_text", _raise_read_error)

    assert list(_docs_drift_sources(snapshot, tmp_path, {})) == []
    assert doc_key in snapshot.nodes


def test_targeted_apply_required_anchor_labels_identifies_missing_base_labels() -> None:
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    class_surface = snapshot.add_node("class_surface", CLASS_PKG_EXAMPLE)
    complexity_candidate = snapshot.add_node(
        "complexity_candidate", COMPLEXITY_PKG_EXAMPLE
    )
    snapshot.add_relation(project, "CONTAINS", complexity_candidate)
    snapshot.add_relation(class_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate)
    snapshot.add_relation(
        complexity_candidate, "CANDIDATE_FOR_SIMPLIFICATION", class_surface
    )

    filtered = _filtered_snapshot(snapshot, only_complexity_layer=True)

    assert _targeted_apply_required_anchor_labels(filtered) == ("class_surface",)


def test_only_label_filter_does_not_pull_external_analysis_anchors() -> None:
    snapshot = GraphSnapshot()
    function_surface = snapshot.add_node("function_surface", "pkg.normalize")
    duplication_cluster = snapshot.add_node(
        "duplication_cluster",
        "adapter_layer:function_surface:abc123",
    )
    complexity_candidate = snapshot.add_node(
        "complexity_candidate",
        "function_surface:pkg.normalize",
    )
    snapshot.add_relation(duplication_cluster, "CONTAINS", function_surface)
    snapshot.add_relation(
        function_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate
    )

    filtered = _filtered_snapshot(
        snapshot,
        only_labels=("duplication_cluster", "function_surface"),
    )

    assert _targeted_apply_required_anchor_labels(filtered) == ()
    assert _targeted_apply_external_anchor_keys(filtered) == ()
    assert (
        NodeKey("duplication_cluster", "adapter_layer:function_surface:abc123"),
        "CONTAINS",
        NodeKey("function_surface", "pkg.normalize"),
    ) in filtered.relations
    assert all(
        relation.relation_type != "HAS_COMPLEXITY_SIGNAL"
        for relation in filtered.relations.values()
    )


def test_targeted_apply_external_anchor_keys_identifies_missing_base_nodes() -> None:
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    class_surface = snapshot.add_node("class_surface", CLASS_PKG_EXAMPLE)
    complexity_candidate = snapshot.add_node(
        "complexity_candidate", COMPLEXITY_PKG_EXAMPLE
    )
    snapshot.add_relation(project, "CONTAINS", complexity_candidate)
    snapshot.add_relation(class_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate)
    snapshot.add_relation(
        complexity_candidate, "CANDIDATE_FOR_SIMPLIFICATION", class_surface
    )

    filtered = _filtered_snapshot(snapshot, only_complexity_layer=True)

    assert _targeted_apply_external_anchor_keys(filtered) == (
        NodeKey("class_surface", CLASS_PKG_EXAMPLE),
    )


def test_ensure_targeted_apply_prerequisites_raises_clear_error_when_anchor_graph_is_empty() -> (
    None
):
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    class_surface = snapshot.add_node("class_surface", CLASS_PKG_EXAMPLE)
    complexity_candidate = snapshot.add_node(
        "complexity_candidate", COMPLEXITY_PKG_EXAMPLE
    )
    snapshot.add_relation(project, "CONTAINS", complexity_candidate)
    snapshot.add_relation(class_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate)
    filtered = _filtered_snapshot(snapshot, only_complexity_layer=True)

    try:
        _ensure_targeted_apply_prerequisites(
            _TargetedApplyPrereqStubClient(),  # type: ignore[arg-type]
            filtered,
            mode_description="complexity-layer targeted sync",
        )
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected prerequisite failure for empty anchor graph")

    assert "Run a base sync first" in message
    assert "`class_surface`" in message


def test_missing_managed_anchor_keys_reports_specific_nodes() -> None:
    class StubClient:
        def query(
            self,
            _statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            assert context == CONTEXT_COMPLEXITY_PREREQ
            assert parameters is not None
            assert parameters["anchors"] == [
                {"label": "class_surface", "name": CLASS_PKG_EXAMPLE},
                {"label": "module_surface", "name": PATH_PKG_EXAMPLE},
            ]
            return [
                {"label": "class_surface", "name": CLASS_PKG_EXAMPLE, "count": 1},
                {"label": "module_surface", "name": PATH_PKG_EXAMPLE, "count": 0},
            ]

    missing = _missing_managed_anchor_keys(
        StubClient(),  # type: ignore[arg-type]
        (
            NodeKey("class_surface", CLASS_PKG_EXAMPLE),
            NodeKey("module_surface", PATH_PKG_EXAMPLE),
        ),
        context=CONTEXT_COMPLEXITY_PREREQ,
    )

    assert missing == (NodeKey("module_surface", PATH_PKG_EXAMPLE),)


def test_ensure_targeted_apply_prerequisites_raises_clear_error_when_specific_anchor_nodes_are_missing() -> (
    None
):
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    class_surface = snapshot.add_node("class_surface", CLASS_PKG_EXAMPLE)
    complexity_candidate = snapshot.add_node(
        "complexity_candidate", COMPLEXITY_PKG_EXAMPLE
    )
    snapshot.add_relation(project, "CONTAINS", complexity_candidate)
    snapshot.add_relation(class_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate)
    filtered = _filtered_snapshot(snapshot, only_complexity_layer=True)

    class StubClient:
        def query(
            self,
            _statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            assert parameters is not None
            if context == "complexity-layer targeted sync prerequisite anchor check":
                return [{"label": "class_surface", "count": 1}]
            if context == CONTEXT_COMPLEXITY_PREREQ:
                return [
                    {"label": "class_surface", "name": CLASS_PKG_EXAMPLE, "count": 0}
                ]
            raise AssertionError(f"Unexpected context: {context}")

    try:
        _ensure_targeted_apply_prerequisites(
            StubClient(),  # type: ignore[arg-type]
            filtered,
            mode_description="complexity-layer targeted sync",
        )
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected prerequisite failure for missing anchor nodes")

    assert "Run a base sync first" in message
    assert "`class_surface:pkg.Example`" in message


def test_live_managed_count_helpers_batch_labels_and_relations() -> None:
    class StubClient:
        def query(
            self,
            statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            assert context is not None
            assert parameters is not None
            if "UNWIND $labels AS label" in statement:
                return [
                    {"label": "retirement_candidate", "count": 4},
                    {"label": "complexity_candidate", "count": 2},
                ]
            if "UNWIND $relation_types AS relation_type" in statement:
                return [
                    {"relation_type": "CANDIDATE_FOR_REMOVAL", "count": 3},
                    {"relation_type": "CANDIDATE_FOR_SIMPLIFICATION", "count": 1},
                ]
            raise AssertionError(f"Unexpected statement: {statement}")

    client = StubClient()

    label_counts = _live_managed_node_counts(
        client,  # type: ignore[arg-type]
        ("retirement_candidate", "complexity_candidate"),
        context=CONTEXT_FAST_AUDIT_LABEL,
    )
    relation_counts = _live_managed_relation_counts(
        client,  # type: ignore[arg-type]
        ("CANDIDATE_FOR_REMOVAL", "CANDIDATE_FOR_SIMPLIFICATION"),
        context="fast audit relation summary",
    )

    assert label_counts == {
        "retirement_candidate": 4,
        "complexity_candidate": 2,
    }
    assert relation_counts == {
        "CANDIDATE_FOR_REMOVAL": 3,
        "CANDIDATE_FOR_SIMPLIFICATION": 1,
    }


def test_git_last_commit_age_days_bulk_batches_history_lookup(monkeypatch) -> None:
    class Result:
        def __init__(self, stdout: str, returncode: int = 0) -> None:
            self.stdout = stdout
            self.returncode = returncode

    calls: list[list[str]] = []

    def _run(
        cmd: list[str],
        _check: bool,
        _capture_output: bool,
        _text: bool,
    ) -> Result:
        calls.append(cmd)
        return Result(
            "__TS__1712448000\nsrc/a.py\nsrc/b.py\n\n__TS__1712361600\nsrc/c.py\n",
        )

    monkeypatch.setattr("scripts.memory.sync.subprocess.run", _run)
    monkeypatch.setattr("scripts.memory.sync._resolve_git_executable", lambda: "git")

    cache: dict[str, int | None] = {}
    result = _git_last_commit_age_days_bulk(
        Path("/repo"),
        [PATH_SRC_A, PATH_SRC_B, PATH_SRC_C],
        date(2026, 4, 10),
        cache,
        chunk_size=10,
    )

    assert len(calls) == 1
    assert calls[0][-3:] == [PATH_SRC_A, PATH_SRC_B, PATH_SRC_C]
    assert result[PATH_SRC_A] is not None
    assert result[PATH_SRC_B] == result[PATH_SRC_A]
    assert result[PATH_SRC_C] is not None
    assert cache == result


def test_build_fast_analysis_audit_report_uses_bulk_count_queries(monkeypatch) -> None:
    class StubSnapshot:
        def stats(self) -> dict[str, object]:
            return {
                "node_count": 6,
                "relation_count": 4,
                "labels": {
                    "retirement_candidate": 4,
                    "complexity_candidate": 2,
                },
                "relation_types": {
                    "CANDIDATE_FOR_REMOVAL": 3,
                    "CANDIDATE_FOR_SIMPLIFICATION": 1,
                },
            }

    snapshot = StubSnapshot()
    query_calls: list[str] = []

    class StubClient:
        def __init__(
            self, base_uri: str, username: str, password: str, database: str
        ) -> None:
            self.base_uri = base_uri
            self.username = username
            self.password = password
            self.database = database

        def query(
            self,
            statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            query_calls.append(context or "")
            if "UNWIND $labels AS label" in statement:
                labels = (
                    list(parameters["labels"]) if isinstance(parameters, dict) else []
                )
                return [
                    {
                        "label": label,
                        "count": int(snapshot.stats()["labels"].get(label, 0)),
                    }
                    for label in labels
                ]
            if "UNWIND $relation_types AS relation_type" in statement:
                relation_types = (
                    list(parameters["relation_types"])
                    if isinstance(parameters, dict)
                    else []
                )
                return [
                    {
                        "relation_type": relation_type,
                        "count": int(
                            snapshot.stats()["relation_types"].get(relation_type, 0)
                        ),
                    }
                    for relation_type in relation_types
                ]
            raise AssertionError(f"Unexpected statement: {statement}")

    monkeypatch.setattr(NEO4J_HTTP_CLIENT_PATH, StubClient)
    root = _repo_root()

    report = build_fast_analysis_audit_report(snapshot, root, LOCALHOST_HTTP_URI)  # type: ignore[arg-type]

    assert query_calls == [
        CONTEXT_FAST_AUDIT_LABEL,
        "fast audit relation summary",
    ]
    assert _critical_analysis_audit_issues(report) == []


def test_build_audit_report_uses_bulk_summary_queries(monkeypatch) -> None:
    snapshot = GraphSnapshot()
    retirement_candidate = snapshot.add_node("retirement_candidate", "retire-me.py")
    complexity_candidate = snapshot.add_node("complexity_candidate", "simplify-me.py")
    snapshot.add_relation(
        retirement_candidate,
        "CANDIDATE_FOR_REMOVAL",
        complexity_candidate,
    )
    query_calls: list[str] = []

    class StubClient:
        def __init__(
            self, base_uri: str, username: str, password: str, database: str
        ) -> None:
            self.base_uri = base_uri
            self.username = username
            self.password = password
            self.database = database

        def query(
            self,
            _statement: str,
            _parameters: dict[str, object] | None = None,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            del _statement, _parameters
            query_calls.append(context or "")
            if context == "full audit label summary":
                return [
                    {
                        "label": "complexity_candidate",
                        "total": 2,
                        "managed": 2,
                        "unmanaged": 0,
                    },
                    {
                        "label": "retirement_candidate",
                        "total": 5,
                        "managed": 4,
                        "unmanaged": 1,
                    },
                ]
            if context == "full audit relation summary":
                return [
                    {"relation_type": "CANDIDATE_FOR_REMOVAL", "count": 3},
                    {"relation_type": "CANDIDATE_FOR_SIMPLIFICATION", "count": 1},
                ]
            if context == "full audit orphan summary":
                return [
                    {
                        "label": "retirement_candidate",
                        "count": 1,
                        "samples": ["stale-module.py"],
                    },
                    {"label": "complexity_candidate", "count": 0, "samples": []},
                ]
            if context == "full audit unmanaged summary":
                return [
                    {
                        "label": "retirement_candidate",
                        "count": 1,
                        "samples": ["legacy-module.py"],
                    },
                    {"label": "complexity_candidate", "count": 0, "samples": []},
                ]
            raise AssertionError(f"Unexpected query context: {context}")

    monkeypatch.setattr(NEO4J_HTTP_CLIENT_PATH, StubClient)
    root = _repo_root()

    report = build_audit_report(snapshot, root, LOCALHOST_HTTP_URI)

    assert query_calls == [
        "full audit label summary",
        "full audit relation summary",
        "full audit orphan summary",
        "full audit unmanaged summary",
    ]
    assert report["live"]["managed_node_total"] == 6
    assert report["live"]["unmanaged_repo_node_total"] == 1
    assert report["live"]["managed_relation_total"] == 4


def test_verify_expected_group_counts_uses_sync_run_for_targeted_relation_checks() -> (
    None
):
    relation_groups = {
        "CANDIDATE_FOR_REMOVAL": [
            {"statement": "RETURN 1", "parameters": {}},
            {"statement": "RETURN 1", "parameters": {}},
        ]
    }
    seen_params: list[dict[str, object]] = []

    class StubClient:
        def query(
            self,
            statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            assert parameters is not None
            seen_params.append(parameters)
            if context == "post-apply node group verification":
                return []
            if context == "post-apply relation group verification":
                assert "coalesce(r.sync_run, '') = $sync_run" in statement
                assert parameters["sync_run"] == "run-123"
                return [{"relation_type": "CANDIDATE_FOR_REMOVAL", "count": 2}]
            raise AssertionError(f"Unexpected query context: {context}")

    _verify_expected_group_counts(
        StubClient(),  # type: ignore[arg-type]
        {},
        relation_groups,
        strict_analysis=False,
        sync_run="run-123",
    )

    assert any(params.get("sync_run") == "run-123" for params in seen_params)


def test_sync_snapshot_uses_current_sync_run_for_prune_stale_verification(
    monkeypatch, tmp_path: Path
) -> None:
    snapshot = GraphSnapshot()
    snapshot.add_node("complexity_candidate", "candidate-1")
    captured_retry_sync_runs: list[str | None] = []
    captured_verify_sync_runs: list[str | None] = []

    class StubClient:
        def execute(self, _statements, *, _context=None) -> dict[str, object]:
            return {"results": [], "errors": []}

        def query(
            self,
            *args: object,
            context=None,
        ) -> list[dict[str, object]]:
            del args, context
            return []

    monkeypatch.setattr(
        "scripts.memory.sync.resolve_neo4j_connection",
        lambda _root, _http_uri: (
            LOCALHOST_HTTP_URI,
            "neo4j",
            "password",
            "neo4j",
        ),
    )
    monkeypatch.setattr(NEO4J_HTTP_CLIENT_PATH, lambda *_args, **_kwargs: StubClient())
    monkeypatch.setattr("scripts.memory.sync._sync_run_id", lambda: "run-123")

    def _retry(*_args, **kwargs) -> None:
        captured_retry_sync_runs.append(kwargs.get("sync_run"))

    def _verify(*_args, **kwargs) -> None:
        captured_verify_sync_runs.append(kwargs.get("sync_run"))

    monkeypatch.setattr("scripts.memory.sync._retry_critical_analysis_groups", _retry)
    monkeypatch.setattr("scripts.memory.sync._verify_expected_group_counts", _verify)

    sync_snapshot(
        snapshot,
        tmp_path,
        None,
        batch_size=10,
        prune_stale=True,
    )

    assert captured_retry_sync_runs == ["run-123"]
    assert captured_verify_sync_runs == ["run-123"]


def test_main_skips_global_post_apply_fast_audit_for_targeted_sync(
    monkeypatch, tmp_path: Path
) -> None:
    snapshot = GraphSnapshot()
    snapshot.add_node("retirement_candidate", "retire-me.py")
    called: dict[str, int] = {"sync_snapshot": 0, "build_fast_analysis_audit_report": 0}

    monkeypatch.setattr("scripts.memory.sync.build_snapshot", lambda _root: snapshot)
    monkeypatch.setattr(
        "scripts.memory.sync._filtered_snapshot",
        lambda current, **_kwargs: current,
    )

    def _sync_snapshot(*_args, **_kwargs) -> None:
        called["sync_snapshot"] += 1

    def _build_fast_analysis_audit_report(*_args, **_kwargs) -> dict[str, object]:
        called["build_fast_analysis_audit_report"] += 1
        return {}

    monkeypatch.setattr("scripts.memory.sync.sync_snapshot", _sync_snapshot)
    monkeypatch.setattr(
        "scripts.memory.sync.build_fast_analysis_audit_report",
        _build_fast_analysis_audit_report,
    )

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--apply",
            "--only-retirement-layer",
        ]
    )

    assert exit_code == 0
    assert called["sync_snapshot"] == 1
    assert called["build_fast_analysis_audit_report"] == 0


def test_complexity_analysis_reuses_declared_surface_metrics_without_ast_parsing(
    monkeypatch,
) -> None:
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    module = snapshot.add_node(
        "module_surface",
        PATH_COMPOSITE_EXAMPLE,
        family_name=FAMILY_APP_COMPOSITE,
        current_cycle_status="current_cycle",
        current_cycle_score=5,
        current_cycle_wip_markers=["wip"],
    )
    class_surface = snapshot.add_node(
        "class_surface",
        "src.bioetl.application.composite.example.ExampleService",
        source_path=PATH_COMPOSITE_EXAMPLE,
    )
    method_surface = snapshot.add_node(
        "method_surface",
        "src.bioetl.application.composite.example.ExampleService.merge",
        source_path=PATH_COMPOSITE_EXAMPLE,
        callable_name="merge",
        branch_count=6,
        nesting_depth=4,
        call_count=5,
        helper_call_count=4,
    )
    pipeline = snapshot.add_node("pipeline_surface", "example_pipeline")
    snapshot.add_relation(module, "DECLARES", class_surface)
    snapshot.add_relation(class_surface, "DECLARES", method_surface)
    snapshot.add_relation(method_surface, "DEPENDS_ON", pipeline)

    monkeypatch.setattr(
        "scripts.memory.sync._read_text",
        lambda _path: "merge helper compat policy",
    )

    def _fail_parse(path: Path) -> None:
        raise AssertionError(
            f"AST parsing should not be used for complexity aggregation: {path}"
        )

    monkeypatch.setattr("scripts.memory.sync._parse_python_ast", _fail_parse)

    _add_complexity_analysis_surfaces(
        snapshot,
        _repo_root(),
        project,
        "2026-04-10",
        {
            "duplication_analysis": {
                "enabled": True,
                "families": {
                    FAMILY_APP_COMPOSITE: {
                        "roots": ["src/bioetl/application/composite"],
                        "package_family": FAMILY_APP_COMPOSITE,
                    }
                },
            },
            "retirement_analysis": {
                "enabled": True,
                "families": [FAMILY_APP_COMPOSITE],
            },
            "complexity_analysis": {
                "enabled": True,
                "families": [FAMILY_APP_COMPOSITE],
                "complexity_score_threshold": 3,
                "removable_score_threshold": 20,
            },
        },
    )

    candidate_key = NodeKey(
        "complexity_candidate",
        "class_surface:src.bioetl.application.composite.example.ExampleService",
    )
    candidate = snapshot.nodes[candidate_key]
    assert candidate.properties["branch_count"] == 6
    assert candidate.properties["nesting_depth"] == 4
    assert candidate.properties["helper_call_count"] == 4


def test_neo4j_http_client_distinguishes_query_runtime_http_errors(monkeypatch) -> None:
    def _raise_http_error(_req: object, _timeout: int = 60) -> object:
        raise error.HTTPError(
            f"{LOCALHOST_HTTP_URI}/db/neo4j/tx/commit",
            400,
            "Bad Request",
            hdrs=None,
            fp=io.BytesIO(b'{"errors":[{"message":"Cypher failed"}]}'),
        )

    monkeypatch.setattr("scripts.memory.sync.request.urlopen", _raise_http_error)
    client = Neo4jHttpClient(LOCALHOST_HTTP_URI, "neo4j", "password", "neo4j")

    try:
        client.execute([], context=CONTEXT_FAST_AUDIT_LABEL)
    except RuntimeError as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected RuntimeError")

    assert CONTEXT_FAST_AUDIT_LABEL in message
    assert "query/runtime error" in message
    assert "transport error" not in message


def test_neo4j_http_client_reports_all_transport_attempts(monkeypatch) -> None:
    responses = [
        error.URLError(TimeoutError("timed out")),
        error.URLError(ConnectionRefusedError(111, "Connection refused")),
    ]

    def _raise_transport_error(_req: object, _timeout: int = 60) -> object:
        raise responses.pop(0)

    monkeypatch.setattr("scripts.memory.sync.request.urlopen", _raise_transport_error)
    client = Neo4jHttpClient(
        HOST_DOCKER_INTERNAL_HTTP_URI, "neo4j", "password", "neo4j"
    )

    try:
        client.execute(
            [],
            context="normalization evidence batch 1/21 pipelines chembl_activity..chembl_activity",
        )
    except RuntimeError as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected RuntimeError")

    assert (
        "normalization evidence batch 1/21 pipelines chembl_activity..chembl_activity"
        in message
    )
    assert "attempts:" in message
    assert f"{HOST_DOCKER_INTERNAL_HTTP_URI}/db/neo4j/tx/commit" in message
    assert f"{LOCALHOST_HTTP_URI}/db/neo4j/tx/commit" in message


def test_snapshot_invariants_are_clean() -> None:
    _, snapshot = _snapshot()

    assert snapshot_invariant_issues(snapshot) == []


def test_snapshot_invariants_require_docs_to_code_drift_edges() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.relation_type == "DESCRIBES"
        and relation.source.label
        in {"doc_source_surface", "doc_artifact", "policy_surface"}
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert "missing docs-to-code drift edges" in issues


def test_snapshot_invariants_require_workflow_job_parent_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.relation_type == "CONTAINS"
        and relation.source.label == "workflow_surface"
        and relation.target.label == "workflow_job_surface"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing workflow_surface -> CONTAINS -> workflow_job_surface links" in issues
    )
    assert any(
        issue.startswith("workflow jobs without workflow parent links:")
        for issue in issues
    )


def test_snapshot_invariants_require_runtime_evidence_support_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.source.label == "runtime_evidence_surface"
        and relation.relation_type in {"BACKED_BY", "DESCRIBED_IN", "WRITES_TO"}
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing runtime_evidence_surface -> WRITES_TO -> storage_surface links"
        in issues
    )
    assert any(
        issue.startswith("runtime evidence surfaces without support links:")
        for issue in issues
    )


def test_snapshot_invariants_require_control_plane_artifact_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.source.label == "runtime_evidence_surface"
        and relation.relation_type == "EMITS_ARTIFACT"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing runtime_evidence_surface -> EMITS_ARTIFACT -> control_plane_artifact_surface links"
        in issues
    )
    assert any(
        issue.startswith("control-plane artifacts without runtime/storage links:")
        for issue in issues
    )


def test_snapshot_invariants_require_run_instance_artifact_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.source.label == "run_instance_surface"
        and relation.relation_type == "REFERENCES_ARTIFACT"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing run_instance_surface -> REFERENCES_ARTIFACT -> control_plane_artifact_surface links"
        in issues
    )
    assert any(
        issue.startswith("run instance surfaces without support links:")
        for issue in issues
    )


def test_snapshot_invariants_require_runtime_state_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.target.label == "runtime_state_surface"
        and relation.relation_type == "HAS_RUNTIME_STATE"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing project -> HAS_RUNTIME_STATE -> runtime_state_surface links" in issues
    )
    assert any(
        issue.startswith("runtime state surfaces without support links:")
        for issue in issues
    )


def test_snapshot_invariants_require_schema_field_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.target.label == "schema_field_surface"
        and relation.relation_type == "HAS_SCHEMA_FIELD"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing storage_surface -> HAS_SCHEMA_FIELD -> schema_field_surface links"
        in issues
    )
    assert any(
        issue.startswith("schema fields without storage/contract/lineage links:")
        for issue in issues
    )
