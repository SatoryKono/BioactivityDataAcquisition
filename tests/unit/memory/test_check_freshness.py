"""Tests for the cross-surface memory freshness gate."""

from __future__ import annotations

from pathlib import Path

from memory.tooling.check_freshness import check_memory_freshness


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
