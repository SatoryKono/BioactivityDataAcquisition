"""Snapshot topology support tests for Neo4j memory sync."""

from __future__ import annotations

import sys

import pytest

from .common import *  # noqa: F403


@pytest.fixture(autouse=True)
def _skip_snapshot_topology_on_windows() -> None:
    if sys.platform.startswith("win"):
        pytest.skip(
            "Snapshot topology tests require full repo walk which is prohibitively slow on Windows"
        )


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
        "src.bioetl.application.composite.merge_service.MergeService",
        "DECLARES",
        "method_surface",
        "src.bioetl.application.composite.merge_service.MergeService.merge",
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
        "doc_source_surface",
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
        "src/bioetl/application/services/control_plane/manifest/service.py",
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
        "doc_source_surface",
        RUN_MANIFEST_LEDGER_DOC_PATH,
        "DESCRIBES",
        "module_surface",
        RUN_MANIFEST_MODULE_PATH,
    ),
    (
        "doc_source_surface",
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
def test_snapshot_contains_expected_relations() -> None:
    _, snapshot = _snapshot()
    relation_keys = _relation_keys(snapshot)

    _assert_relation_membership(relation_keys, EXPECTED_RELATION_KEYS)
    _assert_relation_absence(relation_keys, FORBIDDEN_RELATION_KEYS)


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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


@pytest.mark.timeout(180)
def test_sync_statements_include_management_metadata() -> None:
    snapshot = GraphSnapshot()
    project_key = snapshot.add_node("project", "BioETL")
    module_node = snapshot.add_node("module_surface", "src/example.py")
    snapshot.add_relation(project_key, "CONTAINS", module_node)
    project_node = snapshot.nodes[project_key]
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
def test_filtered_snapshot_docs_drift_preserves_describes_edges() -> None:
    _, snapshot = _snapshot()

    filtered = _filtered_snapshot(snapshot, only_docs_drift=True)
    relation_keys = _relation_keys(filtered)

    assert ("doc_source_surface", RUN_MANIFEST_LEDGER_DOC_PATH) in {
        (key.label, key.name) for key in filtered.nodes
    }
    assert (
        "doc_source_surface",
        RUN_MANIFEST_LEDGER_DOC_PATH,
        "DESCRIBES",
        "module_surface",
        RUN_MANIFEST_MODULE_PATH,
    ) in relation_keys
    assert (
        "module_surface",
        RUN_MANIFEST_MODULE_PATH,
        "DESCRIBED_IN",
        "doc_source_surface",
        RUN_MANIFEST_LEDGER_DOC_PATH,
    ) in relation_keys
    assert any(key.label == "doc_claim_surface" for key in filtered.nodes)
    assert any(
        relation_key[2] == "ASSERTS" and relation_key[3] == "doc_claim_surface"
        for relation_key in relation_keys
    )
    assert ("cli_command_surface", CMD_MEMORY_SYNC) in {
        (key.label, key.name) for key in filtered.nodes
    }


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot topology tests require full repo walk which is prohibitively slow on Windows",
)
@pytest.mark.timeout(300)
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

    monkeypatch.setattr(f"{SYNC_CORE_MODULE_PATH}._read_text", _raise_read_error)

    assert list(_docs_drift_sources(snapshot, tmp_path, {})) == []
    assert doc_key in snapshot.nodes


def test_docs_drift_sources_skips_windows_style_excluded_report_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_path = (
        r"docs\reports\evidence\project-legacy-compatibility-remediation"
        r"\.quarantined-03-synthesis-corrupt-20260521"
        r"\CROSS-SYNTHESIS-project-legacy-compatibility-remediation.md"
    )
    snapshot = GraphSnapshot()
    snapshot.add_node(
        "doc_artifact",
        source_path,
        source_path=source_path,
    )

    def _fail_if_read(_path: Path) -> str:
        raise AssertionError("excluded report paths must not be read")

    monkeypatch.setattr(f"{SYNC_CORE_MODULE_PATH}._read_text", _fail_if_read)

    assert list(_docs_drift_sources(snapshot, tmp_path, {})) == []


def test_docs_drift_sources_skips_absolute_windows_excluded_report_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "BioactivityDataAcquisition2"
    root.mkdir()
    source_path = (
        r"E:\g-drive\05_AI\github\BioactivityDataAcquisition2"
        r"\docs\reports\evidence\project-legacy-compatibility-remediation"
        r"\.quarantined-03-synthesis-corrupt-20260521"
        r"\CROSS-SYNTHESIS-project-legacy-compatibility-remediation.md"
    )
    snapshot = GraphSnapshot()
    snapshot.add_node(
        "doc_artifact",
        source_path,
        source_path=source_path,
    )

    def _fail_if_read(_path: Path) -> str:
        raise AssertionError("absolute excluded report paths must not be read")

    monkeypatch.setattr(f"{SYNC_CORE_MODULE_PATH}._read_text", _fail_if_read)

    assert list(_docs_drift_sources(snapshot, root, {})) == []
