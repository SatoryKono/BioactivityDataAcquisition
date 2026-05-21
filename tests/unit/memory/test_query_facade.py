"""Tests for the unified local memory query facade."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import memory.query as query_module
from memory.query import (
    RagQueryOptions,
    _emit,
    default_rag_chunks_path,
    default_timeline_dir,
    main,
    query_all,
    query_catalog,
    query_entity_impact,
    query_entity_refs,
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


def test_default_generated_memory_paths_prefer_ready_derived_artifacts(
    tmp_path: Path,
) -> None:
    memory_root = tmp_path / "src" / "memory"
    derived_chunks = memory_root / "derived" / "rag" / "manifests" / "chunks.jsonl"
    derived_chunks.parent.mkdir(parents=True, exist_ok=True)
    derived_chunks.write_text('{"id":"chunk-1"}\n', encoding="utf-8")
    derived_events = memory_root / "derived" / "timeline" / "events"
    derived_events.mkdir(parents=True, exist_ok=True)
    (derived_events / "runs.jsonl").write_text('{"id":"run-1"}\n', encoding="utf-8")

    legacy_chunks = memory_root / "rag" / "manifests" / "chunks.jsonl"
    legacy_chunks.parent.mkdir(parents=True, exist_ok=True)
    legacy_chunks.write_text('{"id":"legacy"}\n', encoding="utf-8")
    legacy_events = memory_root / "timeline" / "events"
    legacy_events.mkdir(parents=True, exist_ok=True)
    (legacy_events / "runs.jsonl").write_text('{"id":"legacy-run"}\n', encoding="utf-8")

    assert default_rag_chunks_path(memory_root) == derived_chunks
    assert default_timeline_dir(memory_root) == derived_events


def test_default_generated_memory_paths_fallback_to_legacy_artifacts(
    tmp_path: Path,
) -> None:
    memory_root = tmp_path / "src" / "memory"
    legacy_chunks = memory_root / "rag" / "manifests" / "chunks.jsonl"
    legacy_chunks.parent.mkdir(parents=True, exist_ok=True)
    legacy_chunks.write_text('{"id":"legacy"}\n', encoding="utf-8")
    legacy_events = memory_root / "timeline" / "events"
    legacy_events.mkdir(parents=True, exist_ok=True)
    (legacy_events / "runs.jsonl").write_text('{"id":"legacy-run"}\n', encoding="utf-8")

    assert default_rag_chunks_path(memory_root) == legacy_chunks
    assert default_timeline_dir(memory_root) == legacy_events


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
        RagQueryOptions(
            query="pipeline",
            source_type="code",
            domain="runtime",
            repo_zone="canonical_runtime",
            symbol_kind="function",
            chunks_path=chunks_path,
            limit=5,
        )
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
        RagQueryOptions(
            query="chembl_activity",
            chunks_path=chunks_path,
            limit=5,
            profile="implementation",
        )
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
        RagQueryOptions(
            query="shared",
            chunks_path=chunks_path,
            limit=5,
            file_context="focus.py",
            file_relation_index_path=index_path,
        )
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


def test_query_timeline_auto_refreshes_empty_event_projection_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    (events_dir / "README.md").write_text("Timeline projections live here.\n")
    refresh_calls: list[Path] = []

    def _fake_refresh_all(
        root: Path,
        output_root: Path,
        *,
        include_rag: bool = True,
        include_timeline: bool = True,
        include_graph_export: bool = False,
        rag_build_scope: str = "full",
        rag_focus_query: str | None = None,
        rag_max_sources: int | None = None,
        allow_partial: bool = False,
    ) -> dict[str, object]:
        refresh_calls.append(output_root)
        assert include_rag is False
        assert include_timeline is True
        assert rag_build_scope == "workflow"
        assert rag_focus_query == "memory"
        assert rag_max_sources == 160
        assert allow_partial is True
        refreshed_events = output_root / "timeline" / "events"
        refreshed_events.mkdir(parents=True, exist_ok=True)
        (refreshed_events / "runs.jsonl").write_text(
            json.dumps(
                {
                    "id": "run-1",
                    "event_type": "run.completed",
                    "event_family": "run",
                    "severity": "info",
                    "occurred_at": "2026-04-20T00:00:00Z",
                    "source_refs": ["data/output/control/run_manifest/m1.json"],
                    "payload": {"pipeline_name": "memory"},
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return {"ok": True, "artifacts": [{"kind": "timeline"}]}

    monkeypatch.setattr(query_module, "refresh_all", _fake_refresh_all)

    payload = query_timeline(
        query="memory",
        event_family=None,
        event_type=None,
        events_dir=events_dir,
        limit=5,
        auto_refresh=True,
        refresh_output_root=tmp_path / "refresh",
        refresh_repo_root=tmp_path,
    )

    assert refresh_calls == [tmp_path / "refresh"]
    assert payload["refresh_output_root"] == str(tmp_path / "refresh")
    assert len(payload["results"]) == 1


def test_query_all_auto_refresh_degrades_when_rag_partial_refresh_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events_dir = tmp_path / "events"
    events_dir.mkdir()

    def _fake_refresh_all(
        root: Path,
        output_root: Path,
        *,
        include_rag: bool = True,
        include_timeline: bool = True,
        include_graph_export: bool = False,
        rag_build_scope: str = "full",
        rag_focus_query: str | None = None,
        rag_max_sources: int | None = None,
        allow_partial: bool = False,
    ) -> dict[str, object]:
        assert include_rag is True
        assert include_timeline is True
        assert rag_build_scope == "workflow"
        assert rag_focus_query == "memory"
        assert rag_max_sources == 160
        assert allow_partial is True
        refreshed_events = output_root / "timeline" / "events"
        refreshed_events.mkdir(parents=True, exist_ok=True)
        (refreshed_events / "runs.jsonl").write_text(
            json.dumps(
                {
                    "id": "run-1",
                    "event_type": "run.completed",
                    "event_family": "run",
                    "severity": "info",
                    "occurred_at": "2026-04-20T00:00:00Z",
                    "source_refs": ["data/output/control/run_manifest/m1.json"],
                    "payload": {"pipeline_name": "memory"},
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "ok": False,
            "artifacts": [
                {
                    "kind": "rag",
                    "paths": [],
                    "error": "TimeoutError: synthetic rag timeout",
                },
                {
                    "kind": "timeline",
                    "paths": [str(refreshed_events / "runs.jsonl")],
                },
            ],
        }

    monkeypatch.setattr(query_module, "refresh_all", _fake_refresh_all)

    payload = query_all(
        query="memory",
        chunks_path=tmp_path / "missing" / "chunks.jsonl",
        events_dir=events_dir,
        limit=5,
        auto_refresh=True,
        refresh_output_root=tmp_path / "refresh",
        refresh_repo_root=tmp_path,
    )

    assert payload["degraded"] is True
    assert payload["refresh_report"]["ok"] is False
    assert payload["results"]["timeline"]
    assert payload["results"]["rag"] == []
    assert [item["kind"] for item in payload["missing_artifacts"]] == ["rag_chunks"]


def test_query_timeline_reports_empty_event_projection_dir_without_auto_refresh(
    tmp_path: Path,
) -> None:
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    (events_dir / "README.md").write_text("Timeline projections live here.\n")

    with pytest.raises(FileNotFoundError, match="timeline event projections"):
        query_timeline(
            query="memory",
            event_family=None,
            event_type=None,
            events_dir=events_dir,
        )


def test_query_all_auto_refresh_json_mode_keeps_stdout_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
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

    assert payload["refresh_report"]["ok"] is True
    assert capsys.readouterr().out == ""


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


def test_query_entity_refs_reads_generated_relation_index(tmp_path: Path) -> None:
    index_path = tmp_path / "entity_relations.json"
    index_path.write_text(
        json.dumps(
            {
                "kind": "entity_relation_index",
                "source_snapshot": "snapshot.json",
                "relation_count": 1,
                "entity_count": 2,
                "relation_counts": {"defined_by": 1},
                "by_entity": {
                    "pipeline:chembl_activity": {
                        "name": "chembl_activity",
                        "kind": "pipeline",
                        "path": "configs/entities/chembl/activity.yaml",
                        "outbound": [
                            {
                                "id": "pipeline:chembl_activity|defined_by|config:activity",
                                "direction": "outbound",
                                "relation": "defined_by",
                                "source_id": "pipeline:chembl_activity",
                                "source_name": "chembl_activity",
                                "source_kind": "pipeline",
                                "source_path": "configs/entities/chembl/activity.yaml",
                                "target_id": "config:activity",
                                "target_name": "activity.yaml",
                                "target_kind": "config",
                                "target_path": "configs/entities/chembl/activity.yaml",
                                "confidence": "derived",
                                "provenance": "test",
                                "source_generated_at": "2026-04-17",
                                "evidence": {},
                            }
                        ],
                        "inbound": [],
                    },
                    "config:activity": {
                        "name": "activity.yaml",
                        "kind": "config",
                        "path": "configs/entities/chembl/activity.yaml",
                        "outbound": [],
                        "inbound": [
                            {
                                "id": "pipeline:chembl_activity|defined_by|config:activity",
                                "direction": "inbound",
                                "relation": "defined_by",
                                "source_id": "pipeline:chembl_activity",
                                "source_name": "chembl_activity",
                                "source_kind": "pipeline",
                                "source_path": "configs/entities/chembl/activity.yaml",
                                "target_id": "config:activity",
                                "target_name": "activity.yaml",
                                "target_kind": "config",
                                "target_path": "configs/entities/chembl/activity.yaml",
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

    refs = query_entity_refs(
        entity="chembl_activity",
        direction="outbound",
        index_path=index_path,
    )
    impact = query_entity_impact(entity="config:activity", index_path=index_path)

    assert refs["resolved_entity"] == "pipeline:chembl_activity"
    assert refs["outbound"][0]["target_id"] == "config:activity"
    assert impact["impact_candidates"]["entities_that_reference_query"] == [
        "pipeline:chembl_activity"
    ]
