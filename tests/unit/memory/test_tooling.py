"""Tests for memory refresh and prune tooling."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from memory.tooling.prune import find_prunable_episodic_notes, prune_episodic_notes
from memory.tooling.refresh_all import refresh_all


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
                },
                "edges": {
                    "edge-1": {
                        "source": "file:src/a.py",
                        "target": "file:src/b.py",
                        "edge_type": "references_file",
                    }
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
    assert (output_root / "graph/projections/file_references.jsonl").exists()
    assert (output_root / "graph/indexes/file_relations.json").exists()


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
