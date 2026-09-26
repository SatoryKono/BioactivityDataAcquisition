"""Ratchet and unit coverage for AUD-002 live Neo4j query extract (#10526)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import live_queries

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
LIVE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "live_queries.py"
# Line count on origin/main after the CLI/apply slice (#10644).
_CORE_LOC_BEFORE_LIVE_SLICE = 17021


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_live_queries_own_helpers_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    live_text = LIVE.read_text(encoding="utf-8")
    assert "def _live_managed_node_counts(" not in core_text
    assert "def _live_repo_label_rows(" not in core_text
    assert "def _build_diff_entries(" not in core_text
    assert "def _live_managed_node_counts(" in live_text
    assert _core._live_managed_node_counts is live_queries._live_managed_node_counts
    assert _core._audit_live_summary is live_queries._audit_live_summary
    assert _loc(CORE) < _CORE_LOC_BEFORE_LIVE_SLICE
    assert _loc(LIVE) < 500


def test_count_rows_clause_and_diff_helpers() -> None:
    assert live_queries._managed_sync_run_clause("n", None) == ""
    assert "n.sync_run" in live_queries._managed_sync_run_clause("n", "run-1")
    rows = [
        {"label": "a", "count": 2},
        {"label": "b", "count": 3.0},
        {"label": "skip", "count": "x"},
    ]
    assert live_queries._count_rows_by_key(rows, ("a", "b", "c"), "label") == {
        "a": 2,
        "b": 3,
        "c": 0,
    }
    diff = live_queries._build_diff_entries({"mod": 1}, {"mod": 3, "extra": 1})
    assert diff[0]["name"] == "extra"
    assert diff[1]["delta"] == 2
    assert live_queries._snapshot_count_map({"labels": {"x": 4}}, "labels") == {"x": 4}
    assert live_queries._snapshot_subset_count_map(
        {"labels": {"x": 4, "y": 1}}, "labels", ("x", "z")
    ) == {"x": 4, "z": 0}


def test_live_managed_counts_query_empty_and_mocked_client() -> None:
    assert live_queries._live_managed_node_counts(MagicMock(), (), context="none") == {}
    client = MagicMock()
    client.query.return_value = [{"label": "module_surface", "count": 7}]
    counts = live_queries._live_managed_node_counts(
        client,
        ("module_surface",),
        context="unit",
        sync_run="run-9",
    )
    assert counts == {"module_surface": 7}
    statement, params, kwargs = (
        client.query.call_args.args[0],
        client.query.call_args.args[1],
        client.query.call_args.kwargs,
    )
    assert "UNWIND $labels" in statement
    assert params["sync_run"] == "run-9"
    assert kwargs["context"] == "unit"


def test_audit_live_summary_and_scalar() -> None:
    summary = live_queries._audit_live_summary(
        managed_node_total=2,
        managed_relation_total=1,
        unmanaged_repo_node_total=3,
        label_summary=[{"label": "a", "managed": 2}],
        managed_relation_summary=[{"relation_type": "IMPORTS", "total": 1}],
        orphan_summary=[{"label": "a", "count": 1}],
        unmanaged_summary=[{"label": "a", "count": 3}],
    )
    assert summary["orphan_summary"]["total"] == 1
    assert summary["unmanaged_summary"]["total"] == 3
    client = MagicMock()
    client.query.return_value = [{"n": 4}]
    assert live_queries._live_scalar(client, "RETURN 4 AS n", {}) == 4
    client.query.return_value = []
    assert live_queries._live_scalar(client, "RETURN 0 AS n", {}) == 0
