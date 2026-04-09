"""Tests for deterministic Neo4j repo-graph sync tooling."""

from __future__ import annotations

from pathlib import Path

from scripts.ops.neo4j_memory_sync import (
    _build_diff_entries,
    DEFAULT_INGEST_WAVE,
    DEFAULT_LEGACY_PRUNE_LABELS,
    DEFAULT_MANAGED_BY,
    _delete_managed_wave_nodes_statement,
    build_snapshot,
    derive_http_uri,
    _node_statement,
    _prune_legacy_unmanaged_nodes_statement,
    _prune_stale_nodes_statement,
    _prune_stale_relations_statement,
    _relation_statement,
    _reset_managed_relations_statement,
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
    assert ("layer_family", "domain") in node_keys
    assert ("package_family", "domain/ports") in node_keys
    assert (
        "module_surface",
        "src/bioetl/domain/config/pipeline.py",
    ) in node_keys
    assert ("provider_surface", "chembl") in node_keys
    assert ("entity_config", "chembl_activity") in node_keys
    assert ("composite_config", "composite_activity") in node_keys
    assert ("dashboard_surface", "bioetl-overview-v2") in node_keys
    assert ("policy_surface", "integration and VCR execution policy") in node_keys
    assert ("script_surface", "scripts/dev/run_pytest.sh") in node_keys
    assert ("port_surface", "bioetl.domain.ports") in node_keys
    assert ("adapter_surface", "bioetl.infrastructure.adapters.chembl") in node_keys
    assert ("pipeline_surface", "chembl_activity") in node_keys
    assert ("contract_surface", "chembl.activity") in node_keys
    assert ("alert_surface", "BioETLPipelineRunFailed") in node_keys
    assert (
        "test_artifact",
        "tests/unit/scripts/ops/test_neo4j_memory_sync.py",
    ) in node_keys
    assert ("package_family", "composition/__pycache__") not in node_keys
    assert ("package_family", "infrastructure/__pycache__") not in node_keys
    assert ("package_family", "interfaces/__pycache__") not in node_keys
    assert ("package_family", "composition/control_plane_api.py") not in node_keys
    assert ("package_family", "interfaces/test_cli_checkpoint_list.py") not in node_keys


def test_snapshot_contains_expected_relations() -> None:
    _, snapshot = _snapshot()
    relation_keys = {
        (rel.source.label, rel.source.name, rel.relation_type, rel.target.label, rel.target.name)
        for rel in snapshot.relations.values()
    }

    assert (
        "project",
        "BioETL",
        "HAS_PORT",
        "port_surface",
        "bioetl.domain.ports",
    ) in relation_keys
    assert (
        "project",
        "BioETL",
        "HAS_ADAPTER",
        "adapter_surface",
        "bioetl.infrastructure.adapters.chembl",
    ) in relation_keys
    assert (
        "project",
        "BioETL",
        "HAS_PIPELINE",
        "pipeline_surface",
        "chembl_activity",
    ) in relation_keys
    assert (
        "project",
        "BioETL",
        "HAS_CONTRACT",
        "contract_surface",
        "chembl.activity",
    ) in relation_keys
    assert (
        "project",
        "BioETL",
        "HAS_ALERT",
        "alert_surface",
        "BioETLPipelineRunFailed",
    ) in relation_keys
    assert (
        "project",
        "BioETL",
        "HAS_PROVIDER",
        "provider_surface",
        "chembl",
    ) in relation_keys
    assert (
        "provider_surface",
        "chembl",
        "DEFINES",
        "entity_config",
        "chembl_activity",
    ) in relation_keys
    assert (
        "composite_config",
        "composite_activity",
        "DEPENDS_ON",
        "entity_config",
        "chembl_activity",
    ) in relation_keys
    assert (
        "package_family",
        "domain/config",
        "CONTAINS",
        "module_surface",
        "src/bioetl/domain/config/pipeline.py",
    ) in relation_keys
    assert (
        "project",
        "BioETL",
        "HAS_POLICY_SURFACE",
        "policy_surface",
        "integration and VCR execution policy",
    ) in relation_keys
    assert (
        "policy_surface",
        "integration and VCR execution policy",
        "GOVERNS",
        "test_surface",
        "integration tests",
    ) in relation_keys
    assert (
        "adapter_surface",
        "bioetl.infrastructure.adapters.chembl",
        "DEPENDS_ON",
        "port_surface",
        "bioetl.domain.ports",
    ) in relation_keys
    assert (
        "pipeline_surface",
        "chembl_activity",
        "DEPENDS_ON",
        "adapter_surface",
        "bioetl.infrastructure.adapters.chembl",
    ) in relation_keys
    assert (
        "pipeline_surface",
        "chembl_activity",
        "DEPENDS_ON",
        "contract_surface",
        "chembl.activity",
    ) in relation_keys
    assert (
        "policy_surface",
        "pipeline assembly model",
        "GOVERNS",
        "pipeline_surface",
        "chembl_activity",
    ) in relation_keys
    assert (
        "policy_surface",
        "observability surface model",
        "GOVERNS",
        "alert_surface",
        "BioETLPipelineRunFailed",
    ) in relation_keys
    assert (
        "alert_surface",
        "BioETLPipelineRunFailed",
        "DEPENDS_ON",
        "pipeline_surface",
        "chembl_activity",
    ) in relation_keys
    assert (
        "alert_surface",
        "BioETLProviderFailureRateHigh",
        "DEPENDS_ON",
        "provider_surface",
        "chembl",
    ) in relation_keys
    assert (
        "doc_artifact",
        "scripts/dev/README.md",
        "DESCRIBES",
        "execution_path",
        "bash scripts/dev/run_pytest.sh",
    ) in relation_keys
    assert (
        "script_surface",
        "scripts/dev/run_pytest.sh",
        "PROVIDES",
        "execution_path",
        "bash scripts/dev/run_pytest.sh",
    ) in relation_keys
    assert (
        "test_artifact",
        "tests/unit/scripts/ops/test_neo4j_memory_sync.py",
        "TESTS_LAYER",
        "layer_family",
        "scripts",
    ) not in relation_keys
    assert (
        "layer_family",
        "composition",
        "CONTAINS",
        "module_surface",
        "src/bioetl/composition/control_plane_api.py",
    ) in relation_keys
    assert (
        "test_artifact",
        "tests/integration/interfaces/test_cli_checkpoint_list.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "interfaces/test_cli_checkpoint_list.py",
    ) not in relation_keys
    assert (
        "test_artifact",
        "tests/unit/domain/configs/test_base_configs.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "domain/configs",
    ) not in relation_keys
    assert (
        "test_artifact",
        "tests/unit/domain/hash_policy/test_hash_policy_stability.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "domain/hash_policy",
    ) not in relation_keys
    assert (
        "test_artifact",
        "tests/unit/infrastructure/factories/test_factories.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "infrastructure/factories",
    ) not in relation_keys
    assert (
        "test_artifact",
        "tests/unit/interfaces/factories/test_pipeline_factories.py",
        "TESTS_PACKAGE_FAMILY",
        "package_family",
        "interfaces/factories",
    ) not in relation_keys


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
        "doc_source_surface",
        "doc_artifact",
        "decision",
        "risk",
        "policy_surface",
        "layer_family",
        "package_family",
        "module_surface",
        "port_surface",
        "adapter_surface",
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
