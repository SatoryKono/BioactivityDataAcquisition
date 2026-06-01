"""Tests for expanded graph relation import projections."""

from __future__ import annotations

import pytest

import json
from pathlib import Path

from memory.graph.importers.expanded_json import (
    default_expanded_graph_path,
    load_entity_relation_index,
    load_file_relation_index,
    load_module_relation_index,
    query_entity_relations,
    query_file_neighborhood,
    query_file_relations,
    query_module_neighborhood,
    query_module_relations,
    write_expanded_graph_relation_artifacts,
)


pytestmark = pytest.mark.unit

def _write_expanded_graph(path: Path) -> None:
    payload = {
        "meta": {"generated_at": "2026-04-17", "node_count": 3, "edge_count": 2},
        "nodes": {
            "file:src/a.py": {
                "id": "file:src/a.py",
                "node_type": "File",
                "source_path": "src/a.py",
                "label": "a.py",
            },
            "file:src/b.py": {
                "id": "file:src/b.py",
                "node_type": "File",
                "source_path": "src/b.py",
                "label": "b.py",
            },
            "file:src/c.py": {
                "id": "file:src/c.py",
                "node_type": "File",
                "source_path": "src/c.py",
                "label": "c.py",
            },
            "mod:pkg.a": {
                "id": "mod:pkg.a",
                "node_type": "Module",
                "source_path": "src/a.py",
                "label": "pkg.a",
            },
            "mod:pkg.b": {
                "id": "mod:pkg.b",
                "node_type": "Module",
                "source_path": "src/b.py",
                "label": "pkg.b",
            },
            "mod:pkg.c": {
                "id": "mod:pkg.c",
                "node_type": "Module",
                "source_path": "src/c.py",
                "label": "pkg.c",
            },
            "pipeline:chembl_activity": {
                "id": "pipeline:chembl_activity",
                "node_type": "Pipeline",
                "source_path": "configs/entities/chembl/activity.yaml",
                "label": "chembl_activity",
                "meta": {"provider": "chembl", "entity": "activity"},
            },
            "config:configs/entities/chembl/activity.yaml": {
                "id": "config:configs/entities/chembl/activity.yaml",
                "node_type": "Config",
                "source_path": "configs/entities/chembl/activity.yaml",
                "label": "activity.yaml",
            },
            "artifact:silver/chembl/activity": {
                "id": "artifact:silver/chembl/activity",
                "node_type": "Silver table",
                "source_path": "data/output/silver/chembl/activity",
                "label": "silver/chembl/activity",
            },
        },
        "edges": {
            "src/a.py|references_file|src/b.py": {
                "source": "file:src/a.py",
                "target": "file:src/b.py",
                "edge_type": "references_file",
                "meta": {"statement_count": 2},
            },
            "src/b.py|references_file|src/c.py": {
                "source": "file:src/b.py",
                "target": "file:src/c.py",
                "edge_type": "references_file",
                "meta": {"statement_count": 1},
            },
            "pkg.a|references|pkg.b": {
                "source": "mod:pkg.a",
                "target": "mod:pkg.b",
                "edge_type": "references",
                "meta": {"statement_count": 2},
            },
            "pkg.b|references|pkg.c": {
                "source": "mod:pkg.b",
                "target": "mod:pkg.c",
                "edge_type": "references",
                "meta": {"statement_count": 1},
            },
            "chembl_activity|configured_by|activity": {
                "source": "pipeline:chembl_activity",
                "target": "config:configs/entities/chembl/activity.yaml",
                "edge_type": "configured_by",
                "meta": {"source": "pipeline_config"},
            },
            "chembl_activity|writes_to|silver_activity": {
                "source": "pipeline:chembl_activity",
                "target": "artifact:silver/chembl/activity",
                "edge_type": "writes_to",
                "meta": {"layer": "silver"},
            },
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_default_expanded_graph_path_points_to_memory_projection_surface(
    tmp_path: Path,
) -> None:
    assert default_expanded_graph_path(tmp_path) == (
        tmp_path
        / "src"
        / "memory"
        / "graph"
        / "projections"
        / "bioetl_knowledge_graph_expanded.json"
    )


def test_expanded_graph_import_writes_file_relation_projection_and_index(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "bioetl_knowledge_graph_expanded.json"
    _write_expanded_graph(snapshot_path)

    projection_path, index_path, summary = write_expanded_graph_relation_artifacts(
        snapshot_path,
        tmp_path / "memory",
    )

    assert summary["relation_count"] == 2
    assert summary["module_relation_count"] == 2
    assert projection_path.exists()
    assert index_path.exists()
    assert Path(summary["module_projection_path"]).exists()
    assert Path(summary["module_index_path"]).exists()
    assert len(projection_path.read_text(encoding="utf-8").splitlines()) == 2


def test_file_relation_index_queries_direct_refs_and_neighborhood(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "bioetl_knowledge_graph_expanded.json"
    _write_expanded_graph(snapshot_path)
    _, index_path, _ = write_expanded_graph_relation_artifacts(
        snapshot_path,
        tmp_path / "memory",
    )
    index = load_file_relation_index(index_path)

    refs = query_file_relations(index, "a.py", direction="outbound")
    neighborhood = query_file_neighborhood(index, "src/a.py", depth=2)

    assert refs["resolved_path"] == "src/a.py"
    assert refs["outbound"][0]["target_path"] == "src/b.py"
    assert neighborhood["nodes"] == ["src/a.py", "src/b.py", "src/c.py"]
    assert len(neighborhood["edges"]) == 2


def test_module_relation_index_queries_direct_refs_and_neighborhood(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "bioetl_knowledge_graph_expanded.json"
    _write_expanded_graph(snapshot_path)
    _, _, summary = write_expanded_graph_relation_artifacts(
        snapshot_path,
        tmp_path / "memory",
    )
    index = load_module_relation_index(Path(summary["module_index_path"]))

    refs = query_module_relations(index, "a", direction="outbound")
    neighborhood = query_module_neighborhood(index, "pkg.a", depth=2)

    assert refs["resolved_module"] == "pkg.a"
    assert refs["outbound"][0]["target_name"] == "pkg.b"
    assert neighborhood["nodes"] == ["pkg.a", "pkg.b", "pkg.c"]
    assert len(neighborhood["edges"]) == 2


def test_entity_relation_index_includes_pipeline_docs_tests_configs_and_adr_refs(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "bioetl_knowledge_graph_expanded.json"
    _write_expanded_graph(snapshot_path)
    repo_root = tmp_path / "repo"
    (repo_root / "configs/quality").mkdir(parents=True)
    (repo_root / "configs/quality/test_matrix.yaml").write_text(
        "entity_test_ownership:\n"
        "  chembl.activity:\n"
        "    - tests/integration/pipelines/test_chembl_activity.py\n",
        encoding="utf-8",
    )
    (repo_root / "docs/04-reference/pipelines/chembl").mkdir(parents=True)
    (repo_root / "docs/04-reference/providers/chembl").mkdir(parents=True)
    (repo_root / "docs/04-reference/pipelines/chembl/05-activity-spec.md").write_text(
        "# Activity spec\n",
        encoding="utf-8",
    )
    (repo_root / "docs/04-reference/providers/chembl/activity.md").write_text(
        "# Activity provider\n",
        encoding="utf-8",
    )
    (repo_root / "docs/03-guides").mkdir(parents=True)
    (repo_root / "docs/03-guides/config-policy.md").write_text(
        "# Config policy\n\nConstrains configs/entities/chembl/activity.yaml.\n",
        encoding="utf-8",
    )
    (repo_root / "docs/02-architecture/decisions").mkdir(parents=True)
    (repo_root / "docs/02-architecture/decisions/ADR-999-test.md").write_text(
        "# ADR test\n\n"
        "**Supersedes:** [ADR-998](ADR-998-old.md)\n"
        "**Amends:** [ADR-997](ADR-997-amended.md)\n\n"
        "Constrains configs/entities/chembl/activity.yaml.\n",
        encoding="utf-8",
    )
    (repo_root / "docs/02-architecture/decisions/ADR-998-old.md").write_text(
        "# ADR old\n",
        encoding="utf-8",
    )
    (repo_root / "docs/02-architecture/decisions/ADR-997-amended.md").write_text(
        "# ADR amended\n",
        encoding="utf-8",
    )
    (repo_root / "docs/05-operations/runbooks").mkdir(parents=True)
    (repo_root / "docs/05-operations/runbooks/pipeline-failure-dq.md").write_text(
        "# Pipeline Failure: High DQ Rate (P1)\n",
        encoding="utf-8",
    )

    _, _, summary = write_expanded_graph_relation_artifacts(
        snapshot_path,
        tmp_path / "memory",
        repo_root=repo_root,
    )
    index = load_entity_relation_index(Path(summary["entity_index_path"]))
    refs = query_entity_relations(index, "chembl_activity", direction="outbound")

    relations = {item["relation"] for item in refs["outbound"]}
    assert {"defined_by", "described_by", "emits_artifact", "tested_by"} <= relations
    assert refs["outbound"][0]["source_kind"] == "Pipeline"
    artifact_refs = [
        item for item in refs["outbound"] if item["relation"] == "emits_artifact"
    ]
    assert artifact_refs[0]["target_id"] == "artifact:silver/chembl/activity"
    assert index["relation_counts"]["amends"] == 1
    assert index["relation_counts"]["constrains"] == 2
    assert index["relation_counts"]["emits_artifact"] == 1
    assert index["relation_counts"]["mitigates"] == 1
    assert index["relation_counts"]["supersedes"] == 1
    assert index["relation_counts"]["tested_by"] == 2

    config_refs = query_entity_relations(
        index,
        "config:configs/entities/chembl/activity.yaml",
        direction="outbound",
        relation="tested_by",
    )
    assert config_refs["outbound"][0]["target_kind"] == "Test"

    doc_refs = query_entity_relations(
        index,
        "docs/03-guides/config-policy.md",
        direction="outbound",
        relation="constrains",
    )
    assert doc_refs["outbound"][0]["target_id"] == (
        "config:configs/entities/chembl/activity.yaml"
    )

    adr_refs = query_entity_relations(
        index,
        "ADR-999-test.md",
        direction="outbound",
    )
    assert {"amends", "constrains", "supersedes"} <= {
        item["relation"] for item in adr_refs["outbound"]
    }

    runbook_refs = query_entity_relations(
        index,
        "pipeline-failure-dq.md",
        direction="outbound",
        relation="mitigates",
    )
    assert runbook_refs["outbound"][0]["target_id"] == (
        "failure_mode:pipeline-failure-high-dq-rate"
    )
