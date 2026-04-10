"""Tests for deterministic Neo4j repo-graph sync tooling."""

from __future__ import annotations

from pathlib import Path

from scripts.ops.neo4j_memory_sync import (
    _build_diff_entries,
    DEFAULT_INGEST_WAVE,
    DEFAULT_LEGACY_PRUNE_LABELS,
    DEFAULT_MANAGED_BY,
    _delete_managed_wave_nodes_statement,
    NodeKey,
    build_snapshot,
    derive_http_uri,
    _node_statement,
    _prune_legacy_unmanaged_nodes_statement,
    _prune_stale_nodes_statement,
    _prune_stale_relations_statement,
    _relation_statement,
    _reset_managed_relations_statement,
    snapshot_invariant_issues,
)


def _snapshot() -> tuple[Path, object]:
    root = Path(__file__).resolve().parents[4]
    return root, build_snapshot(root, verified_at="2026-04-09")


def test_derive_http_uri_from_bolt() -> None:
    assert derive_http_uri("bolt://localhost:7687") == "http://localhost:7474"
    assert derive_http_uri("neo4j+s://graph.example.com:7687") == "https://graph.example.com:7474"


def test_snapshot_contains_core_repo_surfaces() -> None:
    _, snapshot = _snapshot()
    node_keys = {(key.label, key.name) for key in snapshot.nodes}

    assert ("project", "BioETL") in node_keys
    assert ("repo_zone", "src") in node_keys
    assert ("repo_zone", "docs") in node_keys
    assert ("directory_surface", "src/bioetl/application/core") in node_keys
    assert ("directory_surface", "configs/entities/chembl") in node_keys
    assert ("directory_surface", "tests/architecture") in node_keys
    assert ("directory_surface", "docs/02-architecture/diagrams") in node_keys
    assert ("directory_surface", "scripts/ops") in node_keys
    assert ("directory_surface", "grafana/dashboards") in node_keys
    assert ("file_surface", "src/bioetl/application/core/record_normalization_processor.py") in node_keys
    assert ("file_surface", "configs/entities/chembl/activity.yaml") in node_keys
    assert ("file_surface", "docs/02-architecture/diagrams/README.md") in node_keys
    assert ("file_surface", "scripts/ops/__main__.py") in node_keys
    assert ("file_surface", "tests/architecture/test_diagram_quality_gates.py") in node_keys
    assert ("file_surface", "grafana/dashboards/bioetl-runtime.json") in node_keys
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
        "src.bioetl.domain.normalization.profiles.chembl_activity._normalize_text",
    ) in node_keys
    assert (
        "method_surface",
        "src.bioetl.application.composite.merger.MergeService.merge",
    ) in node_keys
    assert any(label == "retirement_candidate" for label, _ in node_keys)
    assert any(label == "development_cycle_surface" for label, _ in node_keys)
    assert any(label == "complexity_candidate" for label, _ in node_keys)
    assert ("provider_surface", "chembl") in node_keys
    assert ("entity_config", "chembl_activity") in node_keys
    assert ("composite_config", "composite_activity") in node_keys
    assert ("dashboard_surface", "bioetl-overview-v2") in node_keys
    assert ("doc_source_surface", "architecture diagrams hub") in node_keys
    assert ("doc_source_surface", "diagram governance workflow") in node_keys
    assert ("doc_source_surface", "normalization plan") in node_keys
    assert ("doc_source_surface", "pipeline normalization matrix") in node_keys
    assert ("policy_surface", "integration and VCR execution policy") in node_keys
    assert ("policy_surface", "diagram governance policy") in node_keys
    assert ("script_surface", "scripts/dev/run_pytest.sh") in node_keys
    assert ("script_surface", "scripts/diagrams/__main__.py") in node_keys
    assert ("script_surface", "scripts/docs/__main__.py") in node_keys
    assert ("script_surface", "scripts/schema/__main__.py") in node_keys
    assert ("script_surface", "scripts/ops/__main__.py") in node_keys
    assert ("script_surface", "scripts/qa/__main__.py") in node_keys
    assert ("port_surface", "bioetl.domain.ports") in node_keys
    assert (
        "port_surface",
        "bioetl.domain.ports.runtime.runner.RunnablePort",
    ) in node_keys
    assert ("adapter_surface", "bioetl.infrastructure.adapters.chembl") in node_keys
    assert (
        "adapter_impl_surface",
        "bioetl.infrastructure.adapters.chembl.client",
    ) in node_keys
    assert ("pipeline_surface", "chembl_activity") in node_keys
    assert ("contract_surface", "chembl.activity") in node_keys
    assert ("alert_surface", "BioETLPipelineRunFailed") in node_keys
    assert ("execution_path", "uv run python -m bioetl run --pipeline") in node_keys
    assert ("execution_path", "uv run python -m scripts.diagrams lint") in node_keys
    assert ("execution_path", "uv run python -m scripts.docs verify") in node_keys
    assert ("execution_path", "uv run python -m scripts.schema validate-configs") in node_keys
    assert (
        "execution_path",
        "uv run python -m scripts.docs generate-pipeline-normalization-matrix --check",
    ) in node_keys
    assert ("execution_path", "python -m scripts.ops sync-neo4j-memory --report /tmp/neo4j-memory-audit.json") in node_keys
    assert (
        "execution_path",
        "python -m scripts.qa report-normalization-fallback-inventory --limit 20",
    ) in node_keys
    assert ("quality_gate", "diagram quality gates") in node_keys
    assert any(label == "duplication_cluster" for label, _ in node_keys)
    assert (
        "test_artifact",
        "tests/unit/scripts/ops/test_neo4j_memory_sync.py",
    ) in node_keys
    assert ("package_family", "composition/__pycache__") not in node_keys
    assert ("package_family", "infrastructure/__pycache__") not in node_keys
    assert ("package_family", "interfaces/__pycache__") not in node_keys
    assert ("directory_surface", "docs/99-archive") not in node_keys
    assert ("directory_surface", "docs/reports/generated") not in node_keys
    assert ("directory_surface", "scripts/archive") not in node_keys
    assert ("directory_surface", "docs/02-architecture/diagrams/views/svg") not in node_keys
    assert ("package_family", "composition/control_plane_api.py") not in node_keys
    assert ("package_family", "interfaces/test_cli_checkpoint_list.py") not in node_keys


RelationKey = tuple[str, str, str, str, str]

EXPECTED_RELATION_KEYS: tuple[RelationKey, ...] = (
    ("project", "BioETL", "HAS_REPO_ZONE", "repo_zone", "src"),
    ("repo_zone", "src", "CONTAINS", "directory_surface", "src"),
    ("directory_surface", "src/bioetl/domain", "HOUSES", "layer_family", "domain"),
    ("directory_surface", "src/bioetl/domain/config", "HOUSES", "package_family", "domain/config"),
    ("directory_surface", "src/bioetl/application/core", "HOUSES", "module_surface", "src/bioetl/application/core/record_normalization_processor.py"),
    ("directory_surface", "src/bioetl/application/core", "CONTAINS", "file_surface", "src/bioetl/application/core/record_normalization_processor.py"),
    ("file_surface", "src/bioetl/application/core/record_normalization_processor.py", "BACKS", "module_surface", "src/bioetl/application/core/record_normalization_processor.py"),
    ("directory_surface", "configs/entities/chembl", "CONTAINS", "file_surface", "configs/entities/chembl/activity.yaml"),
    ("directory_surface", "configs/entities/chembl", "HOUSES", "entity_config", "chembl_activity"),
    ("file_surface", "configs/entities/chembl/activity.yaml", "BACKS", "entity_config", "chembl_activity"),
    ("directory_surface", "docs/02-architecture/diagrams", "CONTAINS", "file_surface", "docs/02-architecture/diagrams/README.md"),
    ("directory_surface", "docs/02-architecture/diagrams", "HOUSES", "doc_source_surface", "architecture diagrams hub"),
    ("file_surface", "docs/02-architecture/diagrams/README.md", "BACKS", "doc_artifact", "docs/02-architecture/diagrams/README.md"),
    ("directory_surface", "docs/03-guides", "HOUSES", "doc_source_surface", "testing guide"),
    ("directory_surface", "docs/03-guides/dashboards", "HOUSES", "doc_source_surface", "dashboard extension guide"),
    ("directory_surface", "docs/04-reference/contracts", "HOUSES", "doc_artifact", "docs/04-reference/contracts/run-manifest-ledger.md"),
    ("directory_surface", "docs/05-operations/runbooks", "HOUSES", "doc_artifact", "docs/05-operations/runbooks/traceability-signal-ownership.md"),
    ("directory_surface", "scripts/ops", "CONTAINS", "file_surface", "scripts/ops/__main__.py"),
    ("directory_surface", "scripts/ops", "HOUSES", "script_surface", "scripts/ops/__main__.py"),
    ("file_surface", "scripts/ops/__main__.py", "BACKS", "script_surface", "scripts/ops/__main__.py"),
    ("directory_surface", "tests/architecture", "CONTAINS", "file_surface", "tests/architecture/test_diagram_quality_gates.py"),
    ("directory_surface", "tests/architecture", "HOUSES", "test_surface", "architecture tests"),
    ("directory_surface", "tests/architecture", "HOUSES", "test_artifact", "tests/architecture/test_diagram_quality_gates.py"),
    ("file_surface", "tests/architecture/test_diagram_quality_gates.py", "BACKS", "test_artifact", "tests/architecture/test_diagram_quality_gates.py"),
    ("directory_surface", "grafana/dashboards", "CONTAINS", "file_surface", "grafana/dashboards/bioetl-runtime.json"),
    ("directory_surface", "grafana/dashboards", "HOUSES", "dashboard_surface", "bioetl-runtime"),
    ("file_surface", "grafana/dashboards/bioetl-runtime.json", "BACKS", "dashboard_surface", "bioetl-runtime"),
    ("directory_surface", "configs/contracts", "HOUSES", "contract_surface", "chembl.activity"),
    ("directory_surface", "configs/contracts/chembl", "HOUSES", "contract_surface", "chembl.activity"),
    ("directory_surface", "configs/quality", "HOUSES", "policy_surface", "integration and VCR execution policy"),
    ("module_surface", "src/bioetl/infrastructure/adapters/base.py", "DECLARES", "class_surface", "src.bioetl.infrastructure.adapters.base.BaseHttpAdapter"),
    ("module_surface", "src/bioetl/domain/normalization/profiles/chembl_activity.py", "DECLARES", "function_surface", "src.bioetl.domain.normalization.profiles.chembl_activity._normalize_text"),
    ("class_surface", "src.bioetl.application.composite.merger.MergeService", "DECLARES", "method_surface", "src.bioetl.application.composite.merger.MergeService.merge"),
    ("project", "BioETL", "HAS_PORT", "port_surface", "bioetl.domain.ports"),
    ("project", "BioETL", "HAS_ADAPTER", "adapter_surface", "bioetl.infrastructure.adapters.chembl"),
    ("project", "BioETL", "HAS_PIPELINE", "pipeline_surface", "chembl_activity"),
    ("project", "BioETL", "HAS_CONTRACT", "contract_surface", "chembl.activity"),
    ("project", "BioETL", "HAS_ALERT", "alert_surface", "BioETLPipelineRunFailed"),
    ("project", "BioETL", "HAS_PROVIDER", "provider_surface", "chembl"),
    ("provider_surface", "chembl", "DEFINES", "entity_config", "chembl_activity"),
    ("composite_config", "composite_activity", "DEPENDS_ON", "entity_config", "chembl_activity"),
    ("package_family", "domain/config", "CONTAINS", "module_surface", "src/bioetl/domain/config/pipeline.py"),
    ("project", "BioETL", "HAS_DOC_SOURCE_SURFACE", "doc_source_surface", "architecture diagrams hub"),
    ("policy_surface", "diagram governance policy", "GOVERNS", "quality_gate", "diagram quality gates"),
    ("policy_surface", "diagram governance policy", "GOVERNS", "test_surface", "architecture tests"),
    ("policy_surface", "diagram governance policy", "GOVERNS", "doc_source_surface", "diagram governance workflow"),
    ("project", "BioETL", "HAS_POLICY_SURFACE", "policy_surface", "integration and VCR execution policy"),
    ("script_surface", "scripts/diagrams/__main__.py", "PROVIDES", "execution_path", "uv run python -m scripts.diagrams lint"),
    ("execution_path", "uv run python -m scripts.diagrams lint", "EXECUTES_GATE", "quality_gate", "diagram quality gates"),
    ("script_surface", "scripts/docs/__main__.py", "PROVIDES", "execution_path", "uv run python -m scripts.docs verify"),
    ("execution_path", "uv run python -m scripts.docs verify", "EXECUTES_GATE", "quality_gate", "docs verification"),
    ("script_surface", "scripts/schema/__main__.py", "PROVIDES", "execution_path", "uv run python -m scripts.schema validate-configs"),
    ("execution_path", "uv run python -m scripts.schema validate-configs", "EXECUTES_GATE", "quality_gate", "config validation"),
    ("script_surface", "scripts/ops/__main__.py", "PROVIDES", "execution_path", "python -m scripts.ops sync-neo4j-memory --report /tmp/neo4j-memory-audit.json"),
    ("policy_surface", "integration and VCR execution policy", "GOVERNS", "test_surface", "integration tests"),
    ("adapter_surface", "bioetl.infrastructure.adapters.chembl", "CONTAINS", "adapter_impl_surface", "bioetl.infrastructure.adapters.chembl.client"),
    ("adapter_impl_surface", "bioetl.infrastructure.adapters.chembl.client", "DEPENDS_ON", "port_surface", "bioetl.domain.ports.observability.logging.LoggerPort"),
    ("adapter_surface", "bioetl.infrastructure.adapters.chembl", "DEPENDS_ON", "port_surface", "bioetl.domain.ports.observability.logging.LoggerPort"),
    ("pipeline_surface", "chembl_activity", "DEPENDS_ON", "adapter_surface", "bioetl.infrastructure.adapters.chembl"),
    ("pipeline_surface", "chembl_activity", "DEPENDS_ON", "contract_surface", "chembl.activity"),
    ("pipeline_surface", "chembl_activity", "DEPENDS_ON", "module_surface", "src/bioetl/application/core/record_normalization_processor.py"),
    ("pipeline_surface", "chembl_activity", "DEPENDS_ON", "module_surface", "src/bioetl/domain/normalization/profiles/_chembl_activity_fields.py"),
    ("entity_config", "chembl_activity", "DEPENDS_ON", "module_surface", "src/bioetl/domain/normalization/chembl.py"),
    ("pipeline_surface", "crossref_publication", "DEPENDS_ON", "module_surface", "src/bioetl/application/core/record_normalization_processor.py"),
    ("entity_config", "crossref_publication", "DEPENDS_ON", "module_surface", "src/bioetl/domain/normalization/text.py"),
    ("pipeline_surface", "composite_activity", "DEPENDS_ON", "module_surface", "src/bioetl/application/composite/join_key_normalization.py"),
    ("contract_surface", "pubmed.publication", "DEPENDS_ON", "module_surface", "src/bioetl/domain/schemas/common/publication_base.py"),
    ("contract_surface", "chembl.activity", "BACKED_BY", "config_artifact", "configs/contracts/chembl/activity.yaml"),
    ("contract_surface", "chembl.activity", "DESCRIBED_IN", "doc_artifact", "docs/04-reference/contracts/run-manifest-ledger.md"),
    ("contract_surface", "chembl.activity", "DEPENDS_ON", "module_surface", "src/bioetl/application/services/run_manifest_service.py"),
    ("contract_surface", "chembl.activity", "DEPENDS_ON", "module_surface", "src/bioetl/infrastructure/control_plane/file_effective_config_artifact_store.py"),
    ("contract_surface", "chembl.activity", "DEPENDS_ON", "module_surface", "src/bioetl/interfaces/cli/commands/run_manifest.py"),
    ("contract_surface", "chembl.activity", "DEPENDS_ON", "module_surface", "src/bioetl/application/services/lineage_inspection_service.py"),
    ("contract_surface", "chembl.activity", "DEPENDS_ON", "module_surface", "src/bioetl/composition/bootstrap/cli/lineage.py"),
    ("contract_surface", "chembl.activity", "DESCRIBED_IN", "doc_artifact", "docs/05-operations/runbooks/traceability-signal-ownership.md"),
    ("policy_surface", "pipeline assembly model", "GOVERNS", "pipeline_surface", "chembl_activity"),
    ("policy_surface", "observability surface model", "GOVERNS", "alert_surface", "BioETLPipelineRunFailed"),
    ("pipeline_surface", "chembl_activity", "RUNS_VIA", "execution_path", "uv run python -m bioetl run --pipeline"),
    ("pipeline_surface", "chembl_activity", "VALIDATED_BY", "quality_gate", "pytest"),
    ("pipeline_surface", "chembl_activity", "VALIDATED_BY", "quality_gate", "config validation"),
    ("pipeline_surface", "chembl_activity", "OBSERVED_BY", "dashboard_surface", "bioetl-dq-v2"),
    ("pipeline_surface", "chembl_activity", "TESTED_BY", "test_artifact", "tests/integration/pipelines/test_chembl_activity.py"),
    ("pipeline_surface", "chembl_activity", "TESTED_BY", "test_artifact", "tests/unit/infrastructure/adapters/chembl/test_request_metadata.py"),
    ("pipeline_surface", "chembl_activity", "TESTED_BY", "test_surface", "integration tests"),
    ("pipeline_surface", "composite_activity", "OBSERVED_BY", "dashboard_surface", "bioetl-control-plane-v1"),
    ("alert_surface", "BioETLPipelineRunFailed", "DEPENDS_ON", "pipeline_surface", "chembl_activity"),
    ("alert_surface", "BioETLPipelineRunFailed", "OBSERVED_BY", "dashboard_surface", "bioetl-runtime"),
    ("alert_surface", "BioETLPipelineRunFailed", "DEPENDS_ON", "contract_surface", "chembl.activity"),
    ("alert_surface", "BioETLDQSoftThresholdExceeded", "DEPENDS_ON", "pipeline_surface", "chembl_activity"),
    ("alert_surface", "BioETLProviderFailureRateHigh", "OBSERVED_BY", "dashboard_surface", "bioetl-provider-health-v2"),
    ("alert_surface", "BioETLProviderFailureRateHigh", "DEPENDS_ON", "provider_surface", "chembl"),
    ("alert_surface", "BioETLControlPlaneReadFailureRate", "OBSERVED_BY", "dashboard_surface", "bioetl-control-plane-v1"),
    ("alert_surface", "BioETLControlPlaneReadFailureRate", "DEPENDS_ON", "contract_surface", "chembl.activity"),
    ("doc_artifact", "scripts/dev/README.md", "DESCRIBES", "execution_path", "bash scripts/dev/run_pytest.sh"),
    ("script_surface", "scripts/dev/run_pytest.sh", "PROVIDES", "execution_path", "bash scripts/dev/run_pytest.sh"),
    ("layer_family", "composition", "CONTAINS", "module_surface", "src/bioetl/composition/control_plane_api.py"),
)

FORBIDDEN_RELATION_KEYS: tuple[RelationKey, ...] = (
    ("repo_zone", "docs", "CONTAINS", "directory_surface", "docs/99-archive"),
    ("pipeline_surface", "composite_activity", "OBSERVED_BY", "dashboard_surface", "bioetl-silver-reject-explorer"),
    ("alert_surface", "BioETLDQSoftThresholdExceeded", "DEPENDS_ON", "pipeline_surface", "composite_activity"),
    ("test_artifact", "tests/unit/scripts/ops/test_neo4j_memory_sync.py", "TESTS_LAYER", "layer_family", "scripts"),
    ("test_artifact", "tests/integration/interfaces/test_cli_checkpoint_list.py", "TESTS_PACKAGE_FAMILY", "package_family", "interfaces/test_cli_checkpoint_list.py"),
    ("test_artifact", "tests/unit/domain/configs/test_base_configs.py", "TESTS_PACKAGE_FAMILY", "package_family", "domain/configs"),
    ("test_artifact", "tests/unit/domain/hash_policy/test_hash_policy_stability.py", "TESTS_PACKAGE_FAMILY", "package_family", "domain/hash_policy"),
    ("test_artifact", "tests/unit/infrastructure/factories/test_factories.py", "TESTS_PACKAGE_FAMILY", "package_family", "infrastructure/factories"),
    ("test_artifact", "tests/unit/interfaces/factories/test_pipeline_factories.py", "TESTS_PACKAGE_FAMILY", "package_family", "interfaces/factories"),
)


def _relation_keys(snapshot: object) -> set[RelationKey]:
    return {
        (rel.source.label, rel.source.name, rel.relation_type, rel.target.label, rel.target.name)
        for rel in snapshot.relations.values()
    }


def _assert_relation_membership(relation_keys: set[RelationKey], expected: tuple[RelationKey, ...]) -> None:
    for relation_key in expected:
        assert relation_key in relation_keys


def _assert_relation_absence(relation_keys: set[RelationKey], forbidden: tuple[RelationKey, ...]) -> None:
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
        == "src/bioetl/domain/normalization/profiles/chembl_activity.py"
    )
    assert int(chembl_activity.properties["profile_field_count"]) > 0

    assay_parameters = snapshot.nodes[NodeKey("pipeline_surface", "chembl_assay_parameters")]
    assert assay_parameters.properties["normalization_profile_registered"] is False
    assert int(assay_parameters.properties["fallback_business_field_count"]) > 0
    assert int(assay_parameters.properties["fallback_field_count"]) >= int(
        assay_parameters.properties["fallback_business_field_count"]
    )

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
        node for node in snapshot.nodes.values() if node.key.label == "duplication_cluster"
    ]
    assert duplication_clusters

    cluster_relations = {
        (rel.source.label, rel.relation_type, rel.target.label)
        for rel in snapshot.relations.values()
        if rel.source.label == "duplication_cluster"
    }
    assert ("duplication_cluster", "CONTAINS", "method_surface") in cluster_relations or (
        "duplication_cluster",
        "CONTAINS",
        "function_surface",
    ) in cluster_relations
    assert any(
        rel.source.label == "duplication_cluster" and rel.relation_type == "CAN_PROMOTE_TO"
        for rel in snapshot.relations.values()
    )
    assert any(
        rel.relation_type == "COVERED_BY_TEST" and rel.source.label == "duplication_cluster"
        for rel in snapshot.relations.values()
    )


def test_snapshot_contains_complexity_candidates_with_simplification_links() -> None:
    _, snapshot = _snapshot()

    complexity_candidates = [
        node for node in snapshot.nodes.values() if node.key.label == "complexity_candidate"
    ]
    assert complexity_candidates
    assert any(
        rel.source.label in {"module_surface", "class_surface", "function_surface", "method_surface"}
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
    project_node = snapshot.nodes[next(key for key in snapshot.nodes if key.label == "project" and key.name == "BioETL")]
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
    full_reset_statement = _delete_managed_wave_nodes_statement()
    legacy_prune_statement = _prune_legacy_unmanaged_nodes_statement(["quality_gate", "execution_path"])

    assert "type(r) IN $relation_types" in reset_statement["statement"]
    assert reset_statement["parameters"]["relation_types"] == ["CONTAINS", "DEFINED_BY"]
    assert reset_statement["parameters"]["managed_by"] == DEFAULT_MANAGED_BY
    assert reset_statement["parameters"]["ingest_wave"] == DEFAULT_INGEST_WAVE

    assert "coalesce(r.sync_run, '') <> $sync_run" in prune_relations_statement["statement"]
    assert prune_relations_statement["parameters"]["managed_by"] == DEFAULT_MANAGED_BY
    assert prune_relations_statement["parameters"]["ingest_wave"] == DEFAULT_INGEST_WAVE
    assert prune_relations_statement["parameters"]["sync_run"] == "sync-run-2"

    assert "DETACH DELETE n" in prune_nodes_statement["statement"]
    assert prune_nodes_statement["parameters"]["ingest_wave"] == DEFAULT_INGEST_WAVE
    assert prune_nodes_statement["parameters"]["sync_run"] == "sync-run-2"

    assert "DETACH DELETE n" in full_reset_statement["statement"]
    assert full_reset_statement["parameters"]["ingest_wave"] == DEFAULT_INGEST_WAVE
    assert full_reset_statement["parameters"]["managed_by"] == DEFAULT_MANAGED_BY

    assert "any(label IN labels(n) WHERE label IN $managed_labels)" in legacy_prune_statement["statement"]
    assert "coalesce(n.managed_by, '') = ''" in legacy_prune_statement["statement"]
    assert legacy_prune_statement["parameters"]["managed_labels"] == ["quality_gate", "execution_path"]


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
        "development_cycle_surface",
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


def test_snapshot_invariants_are_clean() -> None:
    _, snapshot = _snapshot()

    assert snapshot_invariant_issues(snapshot) == []
