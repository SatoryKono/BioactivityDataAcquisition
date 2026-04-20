"""Tests for the unified local memory query facade."""

from __future__ import annotations

import json
from pathlib import Path

from memory.query import query_all, query_catalog, query_rag, query_timeline


def test_query_catalog_returns_sources_view() -> None:
    payload = query_catalog("sources")
    assert payload["kind"] == "catalog"
    assert payload["view"] == "sources"
    assert "sources" in payload["payload"]


def test_query_rag_filters_local_manifest(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "id": "a",
            "title": "Overview",
            "content": "alpha context",
            "source_path": "docs/00-project/overview.md",
            "source_type": "doc",
            "domain": "project",
            "repo_zone": "canonical_project_docs",
            "symbol_kind": "markdown_section",
        },
        {
            "id": "b",
            "title": "run",
            "content": "pipeline code",
            "source_path": "src/bioetl/application/service.py",
            "source_type": "code",
            "domain": "runtime",
            "repo_zone": "canonical_runtime",
            "symbol_kind": "function",
        },
    ]
    chunks_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    payload = query_rag(
        query="pipeline",
        source_type="code",
        domain="runtime",
        repo_zone="canonical_runtime",
        symbol_kind="function",
        chunks_path=chunks_path,
        limit=5,
    )
    assert payload["kind"] == "rag"
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == "b"
    assert payload["results"][0]["score"] > 0


def test_query_rag_profile_prefers_runtime_code_for_implementation_tasks(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "id": "doc-1",
            "title": "Activity Pipeline Overview",
            "content": "chembl_activity architecture and docs",
            "source_path": "docs/00-project/overview.md",
            "source_type": "doc",
            "domain": "project",
            "repo_zone": "canonical_project_docs",
            "symbol_kind": "markdown_section",
            "related_refs": ["pipeline::chembl_activity"],
            "graph_node_refs": ["doc_artifact:docs/00-project/overview.md"],
            "confidence": "derived",
        },
        {
            "id": "code-1",
            "title": "run_activity",
            "content": "chembl_activity runtime implementation",
            "source_path": "src/bioetl/application/pipelines/chembl_activity.py",
            "source_type": "code",
            "domain": "runtime",
            "repo_zone": "canonical_runtime",
            "symbol_kind": "function",
            "related_refs": ["pipeline::chembl_activity", "module::src.bioetl.application.pipelines.chembl_activity"],
            "graph_node_refs": ["pipeline_surface:chembl_activity"],
            "confidence": "derived",
        },
    ]
    chunks_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    payload = query_rag(
        query="chembl_activity",
        source_type=None,
        domain=None,
        repo_zone=None,
        symbol_kind=None,
        chunks_path=chunks_path,
        limit=5,
        profile="implementation",
    )
    assert payload["results"][0]["id"] == "code-1"
    assert payload["results"][0]["score"] >= payload["results"][1]["score"]


def test_query_timeline_filters_local_events(tmp_path: Path) -> None:
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    rows = [
        {
            "id": "e1",
            "event_type": "ci.workflow_defined",
            "event_family": "ci",
            "severity": "info",
            "occurred_at": None,
            "source_refs": [".github/workflows/tests.yml"],
        },
        {
            "id": "e2",
            "event_type": "run.manifest_registered",
            "event_family": "run",
            "severity": "info",
            "occurred_at": "2026-04-20T00:00:00Z",
            "source_refs": ["data/output/control/run_manifest/m1.json"],
        },
    ]
    (events_dir / "runs.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    payload = query_timeline(
        query="manifest",
        event_family="run",
        event_type=None,
        events_dir=events_dir,
        limit=5,
    )
    assert payload["kind"] == "timeline"
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == "e2"


def test_query_timeline_profile_prefers_incidents_for_operations_tasks(tmp_path: Path) -> None:
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    rows = [
        {
            "id": "ci-1",
            "event_type": "ci.workflow_defined",
            "event_family": "ci",
            "severity": "info",
            "occurred_at": None,
            "source_refs": [".github/workflows/tests.yml"],
            "related_refs": ["pipeline::chembl_activity"],
            "graph_node_refs": ["workflow_surface:Tests"],
            "confidence": "derived",
            "payload": {"workflow_name": "Tests"},
        },
        {
            "id": "incident-1",
            "event_type": "incident.runbook_defined",
            "event_family": "incident",
            "severity": "warning",
            "occurred_at": None,
            "source_refs": ["docs/05-operations/runbooks/incident-response.md"],
            "related_refs": ["pipeline::chembl_activity", "incident::incident-response"],
            "graph_node_refs": ["doc_artifact:docs/05-operations/runbooks/incident-response.md"],
            "confidence": "derived",
            "payload": {"title": "Incident Response"},
        },
    ]
    (events_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    payload = query_timeline(
        query="chembl_activity",
        event_family=None,
        event_type=None,
        events_dir=events_dir,
        limit=5,
        profile="operations",
    )
    assert payload["results"][0]["id"] == "incident-1"
    assert payload["results"][0]["score"] >= payload["results"][1]["score"]


def test_query_all_aggregates_local_surfaces(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(
        json.dumps(
            {
                "id": "chunk-1",
                "title": "Pipeline",
                "content": "chembl_activity pipeline",
                "source_path": "src/bioetl/application/service.py",
                "source_type": "code",
                "domain": "runtime",
                "repo_zone": "canonical_runtime",
                "symbol_kind": "function",
                "related_refs": ["pipeline::chembl_activity"],
                "graph_node_refs": ["pipeline_surface:chembl_activity"],
                "confidence": "derived",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    (events_dir / "runs.jsonl").write_text(
        json.dumps(
            {
                "id": "run-1",
                "event_type": "run.manifest_registered",
                "event_family": "run",
                "severity": "info",
                "occurred_at": "2026-04-20T00:00:00Z",
                "source_refs": ["data/output/control/run_manifest/m1.json"],
                "related_refs": ["pipeline::chembl_activity"],
                "graph_node_refs": ["pipeline_surface:chembl_activity"],
                "confidence": "derived",
                "payload": {"pipeline_name": "chembl_activity"},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = query_all(
        query="chembl_activity",
        chunks_path=chunks_path,
        events_dir=events_dir,
        limit=5,
    )
    assert payload["kind"] == "all"
    assert len(payload["results"]["rag"]) == 1
    assert len(payload["results"]["timeline"]) == 1
