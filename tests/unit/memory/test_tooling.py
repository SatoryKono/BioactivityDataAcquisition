"""Tests for memory refresh and prune tooling."""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from memory.graph import sync as graph_sync
from memory.tooling import workflow as workflow_module
from memory.tooling.prune import find_prunable_episodic_notes, prune_episodic_notes
from memory.tooling.refresh_all import refresh_all
from tests.helpers.cli_process import run_main_in_process

import pytest

pytestmark = pytest.mark.unit


def _ignore_memory_package_runtime_payloads(
    memory_source_root: Path,
) -> Callable[[str, list[str]], set[str]]:
    def _ignore(directory: str, names: list[str]) -> set[str]:
        relative_dir = Path(directory).relative_to(memory_source_root)
        ignored = {"__pycache__"} & set(names)
        if relative_dir == Path("."):
            ignored.update({"curated", "derived", "episodic"} & set(names))
        if relative_dir == Path("rag"):
            ignored.update({"manifests"} & set(names))
        if relative_dir == Path("timeline"):
            ignored.update({"events"} & set(names))
        if relative_dir == Path("graph"):
            ignored.update({"exports", "indexes", "projections"} & set(names))
        return ignored

    return _ignore


def test_refresh_all_generates_rag_and_timeline_outputs(tmp_path: Path) -> None:
    (tmp_path / "docs/00-project").mkdir(parents=True)
    (tmp_path / "docs/00-project/overview.md").write_text(
        "# Overview\nAlpha\n", encoding="utf-8"
    )
    (tmp_path / "docs/02-architecture/decisions").mkdir(parents=True)
    (tmp_path / "docs/05-operations/runbooks").mkdir(parents=True)
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/tests.yml").write_text(
        "name: Tests\njobs:\n  lint:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )

    output_root = tmp_path / "memory-out"
    summary = refresh_all(tmp_path, output_root, include_graph_export=False)

    assert summary["ok"] is True
    assert (output_root / "rag/manifests/corpus_catalog.json").exists()
    assert (output_root / "timeline/events/ci.jsonl").exists()


def test_refresh_all_can_import_expanded_graph_file_relations(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "bioetl_knowledge_graph_expanded.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "meta": {"generated_at": "2026-04-17"},
                "nodes": {
                    "file:src/a.py": {"source_path": "src/a.py"},
                    "file:src/b.py": {"source_path": "src/b.py"},
                    "mod:pkg.a": {
                        "id": "mod:pkg.a",
                        "node_type": "Module",
                        "source_path": "src/a.py",
                    },
                    "mod:pkg.b": {
                        "id": "mod:pkg.b",
                        "node_type": "Module",
                        "source_path": "src/b.py",
                    },
                },
                "edges": {
                    "edge-1": {
                        "source": "file:src/a.py",
                        "target": "file:src/b.py",
                        "edge_type": "references_file",
                    },
                    "edge-2": {
                        "source": "mod:pkg.a",
                        "target": "mod:pkg.b",
                        "edge_type": "references",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "memory-out"
    summary = refresh_all(
        tmp_path,
        output_root,
        include_rag=False,
        include_timeline=False,
        include_graph_relations=True,
        expanded_graph_path=snapshot_path,
    )

    assert summary["ok"] is True
    assert summary["artifacts"][0]["module_relation_count"] == 1
    assert (output_root / "graph/projections/file_references.jsonl").exists()
    assert (output_root / "graph/indexes/file_relations.json").exists()
    assert (output_root / "graph/projections/module_references.jsonl").exists()
    assert (output_root / "graph/indexes/module_relations.json").exists()


def test_refresh_all_graph_export_uses_direct_snapshot_writer(
    tmp_path: Path, monkeypatch
) -> None:
    output_root = tmp_path / "memory-out"
    called: dict[str, object] = {}

    def _fake_build_snapshot(root: Path):
        called["root"] = root
        return graph_sync.GraphSnapshot()

    def _fake_write_export(path: Path, snapshot: object) -> None:
        called["path"] = path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(graph_sync, "build_snapshot", _fake_build_snapshot)
    monkeypatch.setattr(graph_sync, "_write_export", _fake_write_export)

    summary = refresh_all(
        tmp_path,
        output_root,
        include_rag=False,
        include_timeline=False,
        include_graph_export=True,
    )

    assert summary["ok"] is True
    assert summary["artifacts"][0]["kind"] == "graph"
    assert (output_root / "graph/exports/repo_snapshot.json").exists()
    assert called["root"] == tmp_path


def test_find_prunable_episodic_notes_uses_metadata_ttl(tmp_path: Path) -> None:
    note = tmp_path / "old.json"
    note.write_text(
        json.dumps(
            {
                "task_id": "t-1",
                "created_at": "2026-04-01T00:00:00Z",
                "ttl_days": 7,
            }
        ),
        encoding="utf-8",
    )
    candidates = find_prunable_episodic_notes(
        tmp_path,
        now=datetime(2026, 4, 20, tzinfo=UTC),
    )
    assert len(candidates) == 1
    assert candidates[0].path == str(note)


def test_prune_episodic_notes_apply_removes_expired_files(tmp_path: Path) -> None:
    note = tmp_path / "old.yaml"
    note.write_text(
        "task_id: t-2\ncreated_at: 2026-04-01T00:00:00Z\nttl_days: 7\n",
        encoding="utf-8",
    )
    report = prune_episodic_notes(
        tmp_path,
        apply=True,
        now=datetime(2026, 4, 20, tzinfo=UTC),
    )
    assert report["removed_count"] == 1
    assert not note.exists()


def test_prune_episodic_notes_reports_density_review(tmp_path: Path) -> None:
    for index in range(2):
        note = tmp_path / f"active-{index}.yaml"
        note.write_text(
            "task_id: t-active\ncreated_at: 2026-04-19T00:00:00Z\nttl_days: 14\n",
            encoding="utf-8",
        )

    report = prune_episodic_notes(
        tmp_path,
        max_active=1,
        now=datetime(2026, 4, 20, tzinfo=UTC),
    )

    assert report["candidate_count"] == 0
    assert report["total_count"] == 2
    assert report["active_count"] == 2
    assert report["density_status"] == "review"
    assert report["density_excess"] == 1


def test_prune_episodic_notes_uses_policy_backed_max_active(tmp_path: Path) -> None:
    for index in range(1001):
        note = tmp_path / f"active-{index}.yaml"
        note.write_text(
            "task_id: t-active\ncreated_at: 2026-04-19T00:00:00Z\nttl_days: 14\n",
            encoding="utf-8",
        )

    report = prune_episodic_notes(
        tmp_path,
        now=datetime(2026, 4, 20, tzinfo=UTC),
    )

    assert report["max_active"] == 1000
    assert report["density_status"] == "review"
    assert report["density_excess"] == 1


def test_memory_tooling_package_exports_submodules_lazily() -> None:
    tooling = importlib.reload(importlib.import_module("memory.tooling"))
    for name in ("workflow", "refresh_all"):
        tooling.__dict__.pop(name, None)

    assert "workflow" not in tooling.__dict__

    workflow_module = tooling.workflow
    refresh_module = tooling.refresh_all

    assert workflow_module.__name__ == "memory.tooling.workflow"
    assert refresh_module.__name__ == "memory.tooling.refresh_all"

    query_module = importlib.import_module("memory.query")
    assert callable(query_module.query_all)


def test_memory_workflow_module_help_does_not_emit_runpy_warning() -> None:
    result = run_main_in_process(workflow_module.main, "--help")

    assert result.returncode == 0
    assert "RuntimeWarning" not in result.stderr
    assert "pre-task" in result.stdout
