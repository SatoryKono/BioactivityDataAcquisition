"""Tests for the cross-surface memory freshness gate."""

from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime
import hashlib
import json

from memory.tooling.check_freshness import _check_graph_freshness, check_memory_freshness


def test_current_repository_memory_surfaces_are_fresh() -> None:
    repo_root = Path(__file__).parents[3]
    report = check_memory_freshness(repo_root)

    assert report["ok"], report
    assert {check["surface"] for check in report["checks"]} == {
        "curated-memory",
        "knowledge-graph",
        "mcp-seed",
        "project-catalog",
    }


def test_graph_projection_fails_on_stale_or_mismatched_manifest(tmp_path: Path) -> None:
    graph = tmp_path / "graph"
    (graph / "projections").mkdir(parents=True)
    (graph / "ontology.yaml").write_text("nodes: []\n", encoding="utf-8")
    (graph / "mappings.yaml").write_text("mappings: []\n", encoding="utf-8")
    digest = hashlib.sha256()
    digest.update((graph / "ontology.yaml").read_bytes())
    digest.update((graph / "mappings.yaml").read_bytes())
    (graph / "projections" / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-01-01T00:00:00Z",
                "source_sha256": digest.hexdigest(),
            }
        ),
        encoding="utf-8",
    )

    ok, details = _check_graph_freshness(
        tmp_path, now=datetime(2026, 3, 1, tzinfo=UTC)
    )
    assert not ok
    assert details["age_days"] == 59

    manifest = json.loads(
        (graph / "projections" / "manifest.json").read_text(encoding="utf-8")
    )
    manifest["generated_at"] = "2026-03-01T00:00:00Z"
    manifest["source_sha256"] = "0" * 64
    (graph / "projections" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    ok, details = _check_graph_freshness(
        tmp_path, now=datetime(2026, 3, 1, tzinfo=UTC)
    )
    assert not ok
    assert details["source_identity_matches"] is False
