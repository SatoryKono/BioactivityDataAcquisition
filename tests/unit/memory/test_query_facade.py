"""Tests for the unified local memory query facade."""

from __future__ import annotations

import json
from pathlib import Path

from memory.query import (
    _emit,
    main,
    query_all,
    query_catalog,
    query_file_impact,
    query_file_refs,
    query_module_impact,
    query_module_refs,
    query_rag,
    query_timeline,
)


def test_query_catalog_returns_sources_view() -> None:
    payload = query_catalog("sources")
    assert payload["kind"] == "catalog"
    assert payload["view"] == "sources"
    assert "sources" in payload["payload"]


def test_emit_returns_nonzero_for_failed_payload(capsys) -> None:
    exit_code = _emit({"kind": "diagnostic", "ok": False}, as_json=True)

    assert exit_code == 1
    assert '"ok": false' in capsys.readouterr().out


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


def test_query_rag_profile_prefers_runtime_code_for_implementation_tasks(
    tmp_path: Path,
) -> None:
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
            "related_refs": [
                "pipeline::chembl_activity",
                "module::src.bioetl.application.pipelines.chembl_activity",
            ],
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


def test_query_rag_boosts_file_relation_context(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "id": "unrelated",
            "title": "unrelated",
            "content": "shared implementation context",
            "source_path": "src/unrelated.py",
            "source_type": "code",
            "domain": "runtime",
            "repo_zone": "canonical_runtime",
            "symbol_kind": "function",
        },
        {
            "id": "related",
            "title": "related",
            "content": "shared implementation context",
            "source_path": "src/related.py",
            "source_type": "code",
            "domain": "runtime",
            "repo_zone": "canonical_runtime",
            "symbol_kind": "function",
        },
        {
            "id": "focus",
            "title": "focus",
            "content": "shared implementation context",
            "source_path": "src/focus.py",
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
    index_path = tmp_path / "file_relations.json"
    index_path.write_text(
        json.dumps(
            {
                "kind": "file_relation_index",
                "relation": "references_file",
                "source_snapshot": "snapshot.json",
                "by_file": {
                    "src/focus.py": {
                        "outbound": [
                            {
                                "id": "src/focus.py|references_file|src/related.py",
                                "direction": "outbound",
                                "relation": "references_file",
                                "source_path": "src/focus.py",
                                "target_path": "src/related.py",
                                "confidence": "derived",
                                "provenance": "test",
                                "source_generated_at": "2026-04-17",
                                "evidence": {},
                            }
                        ],
                        "inbound": [],
                    },
                    "src/related.py": {
                        "outbound": [],
                        "inbound": [
                            {
                                "id": "src/focus.py|references_file|src/related.py",
                                "direction": "inbound",
                                "relation": "references_file",
                                "source_path": "src/focus.py",
                                "target_path": "src/related.py",
                                "confidence": "derived",
                                "provenance": "test",
                                "source_generated_at": "2026-04-17",
                                "evidence": {},
                            }
                        ],
                    },
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    payload = query_rag(
        query="shared",
        source_type=None,
        domain=None,
        repo_zone=None,
        symbol_kind=None,
        chunks_path=chunks_path,
        limit=5,
        file_context="focus.py",
        file_relation_index_path=index_path,
    )

    assert [item["id"] for item in payload["results"][:2]] == ["focus", "related"]
    assert "file_context:focus" in payload["results"][0]["ranking_reasons"]
    assert "file_relation:references_file" in payload["results"][1]["ranking_reasons"]


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


def test_query_timeline_profile_prefers_incidents_for_operations_tasks(
    tmp_path: Path,
) -> None:
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
            "related_refs": [
                "pipeline::chembl_activity",
                "incident::incident-response",
            ],
            "graph_node_refs": [
                "doc_artifact:docs/05-operations/runbooks/incident-response.md"
            ],
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


def test_query_cli_reports_missing_manifest_without_traceback(
    tmp_path: Path, capsys
) -> None:
    exit_code = main(
        [
            "rag",
            "--query",
            "memory",
            "--chunks-path",
            str(tmp_path / "missing.jsonl"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Missing RAG chunk manifest" in captured.err
    assert "--auto-refresh" in captured.err
    assert "Traceback" not in captured.err


def test_query_all_auto_refreshes_missing_rebuild_only_artifacts(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs/00-project").mkdir(parents=True)
    (tmp_path / "docs/00-project/overview.md").write_text(
        "# Memory Overview\nMemory retrieval context.\n",
        encoding="utf-8",
    )
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/tests.yml").write_text(
        "name: Tests\njobs:\n  memory-tests:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )

    payload = query_all(
        query="memory",
        chunks_path=tmp_path / "missing" / "chunks.jsonl",
        events_dir=tmp_path / "missing" / "events",
        limit=5,
        auto_refresh=True,
        refresh_output_root=tmp_path / "memory-refresh",
        refresh_repo_root=tmp_path,
    )

    assert payload["refresh_output_root"] == str(tmp_path / "memory-refresh")
    assert payload["refresh_report"]["ok"] is True
    assert len(payload["results"]["rag"]) >= 1
    assert any(item["source_type"] == "workflow" for item in payload["results"]["rag"])


def test_query_file_refs_reads_generated_relation_index(tmp_path: Path) -> None:
    index_path = tmp_path / "file_relations.json"
    index_path.write_text(
        json.dumps(
            {
                "kind": "file_relation_index",
                "relation": "references_file",
                "source_snapshot": "snapshot.json",
                "by_file": {
                    "src/a.py": {
                        "outbound": [
                            {
                                "id": "src/a.py|references_file|src/b.py",
                                "direction": "outbound",
                                "relation": "references_file",
                                "source_path": "src/a.py",
                                "target_path": "src/b.py",
                                "confidence": "derived",
                                "provenance": "test",
                                "source_generated_at": "2026-04-17",
                                "evidence": {},
                            }
                        ],
                        "inbound": [],
                    },
                    "src/b.py": {
                        "outbound": [],
                        "inbound": [
                            {
                                "id": "src/a.py|references_file|src/b.py",
                                "direction": "inbound",
                                "relation": "references_file",
                                "source_path": "src/a.py",
                                "target_path": "src/b.py",
                                "confidence": "derived",
                                "provenance": "test",
                                "source_generated_at": "2026-04-17",
                                "evidence": {},
                            }
                        ],
                    },
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    refs = query_file_refs(
        source_path="a.py",
        direction="outbound",
        index_path=index_path,
    )
    impact = query_file_impact(source_path="src/b.py", index_path=index_path)

    assert refs["resolved_path"] == "src/a.py"
    assert refs["outbound"][0]["target_path"] == "src/b.py"
    assert impact["impact_candidates"]["files_that_reference_query"] == ["src/a.py"]


def test_query_module_refs_reads_generated_relation_index(tmp_path: Path) -> None:
    index_path = tmp_path / "module_relations.json"
    index_path.write_text(
        json.dumps(
            {
                "kind": "module_relation_index",
                "relation": "references",
                "source_snapshot": "snapshot.json",
                "by_module": {
                    "pkg.a": {
                        "outbound": [
                            {
                                "id": "pkg.a|references|pkg.b",
                                "direction": "outbound",
                                "relation": "references",
                                "source_name": "pkg.a",
                                "source_path": "src/a.py",
                                "target_name": "pkg.b",
                                "target_path": "src/b.py",
                                "confidence": "derived",
                                "provenance": "test",
                                "source_generated_at": "2026-04-17",
                                "evidence": {},
                            }
                        ],
                        "inbound": [],
                    },
                    "pkg.b": {
                        "outbound": [],
                        "inbound": [
                            {
                                "id": "pkg.a|references|pkg.b",
                                "direction": "inbound",
                                "relation": "references",
                                "source_name": "pkg.a",
                                "source_path": "src/a.py",
                                "target_name": "pkg.b",
                                "target_path": "src/b.py",
                                "confidence": "derived",
                                "provenance": "test",
                                "source_generated_at": "2026-04-17",
                                "evidence": {},
                            }
                        ],
                    },
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    refs = query_module_refs(
        module_name="a",
        direction="outbound",
        index_path=index_path,
    )
    impact = query_module_impact(module_name="pkg.b", index_path=index_path)

    assert refs["resolved_module"] == "pkg.a"
    assert refs["outbound"][0]["target_name"] == "pkg.b"
    assert impact["impact_candidates"]["modules_that_reference_query"] == ["pkg.a"]
