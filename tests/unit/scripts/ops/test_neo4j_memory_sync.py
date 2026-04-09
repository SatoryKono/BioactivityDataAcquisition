"""Tests for deterministic Neo4j repo-graph sync tooling."""

from __future__ import annotations

from pathlib import Path

from scripts.ops.neo4j_memory_sync import build_snapshot, derive_http_uri


def _snapshot() -> tuple[Path, object]:
    root = Path(__file__).resolve().parents[4]
    return root, build_snapshot(root, verified_at="2026-04-09")


def test_derive_http_uri_from_bolt() -> None:
    assert derive_http_uri("bolt://localhost:7687") == "http://localhost:7474"
    assert derive_http_uri("neo4j+s://graph.example.com:7687") == "https://graph.example.com:7474"


def test_snapshot_contains_core_repo_surfaces() -> None:
    _, snapshot = _snapshot()

    assert ("project", "BioETL") in {(key.label, key.name) for key in snapshot.nodes}
    assert ("layer_family", "domain") in {(key.label, key.name) for key in snapshot.nodes}
    assert ("package_family", "domain/ports") in {(key.label, key.name) for key in snapshot.nodes}
    assert (
        "module_surface",
        "src/bioetl/domain/config/pipeline.py",
    ) in {(key.label, key.name) for key in snapshot.nodes}
    assert ("provider_surface", "chembl") in {(key.label, key.name) for key in snapshot.nodes}
    assert ("entity_config", "chembl_activity") in {(key.label, key.name) for key in snapshot.nodes}
    assert ("composite_config", "composite_activity") in {(key.label, key.name) for key in snapshot.nodes}
    assert ("dashboard_surface", "bioetl-overview-v2") in {(key.label, key.name) for key in snapshot.nodes}
    assert ("script_surface", "scripts/dev/run_pytest.sh") in {(key.label, key.name) for key in snapshot.nodes}
    assert (
        "test_artifact",
        "tests/unit/scripts/ops/test_neo4j_memory_sync.py",
    ) in {(key.label, key.name) for key in snapshot.nodes}


def test_snapshot_contains_expected_relations() -> None:
    _, snapshot = _snapshot()
    relation_keys = {
        (rel.source.label, rel.source.name, rel.relation_type, rel.target.label, rel.target.name)
        for rel in snapshot.relations.values()
    }

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
