"""Ratchet and unit coverage for AUD-002 apply grouping extract (#10526)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import apply_groups
from memory.graph.sync_pkg._core_models import SyncApplyOptions
from memory.graph.sync_pkg.neo4j_statements import _node_statement

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
GROUPS = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "apply_groups.py"
# Line count on origin/main after the live-query slice (#10646).
_CORE_LOC_BEFORE_APPLY_GROUPS_SLICE = 16722


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_apply_groups_own_helpers_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    groups_text = GROUPS.read_text(encoding="utf-8")
    assert "def _statement_groups(" not in core_text
    assert "def _apply_snapshot_statement_groups(" not in core_text
    assert "def _partition_groups(" not in core_text
    assert callable(_core.sync_snapshot)
    assert "def _statement_groups(" in groups_text
    assert _core._statement_groups is apply_groups._statement_groups
    assert _core.DEFAULT_LEGACY_PRUNE_LABELS is apply_groups.DEFAULT_LEGACY_PRUNE_LABELS
    assert _core.ANALYSIS_NODE_LABELS == apply_groups.ANALYSIS_NODE_LABELS
    assert _loc(CORE) < _CORE_LOC_BEFORE_APPLY_GROUPS_SLICE
    assert _loc(GROUPS) < 500


def test_partition_and_batch_sizes() -> None:
    nodes = {
        "module_surface": [{"statement": "n"}],
        "retirement_candidate": [{"statement": "r"}],
        "complexity_candidate": [{"statement": "c"}],
    }
    rels = {
        "IMPORTS": [{"statement": "i"}],
        "CANDIDATE_FOR_REMOVAL": [{"statement": "x"}],
    }
    core_nodes, analysis_nodes, core_rels, analysis_rels = (
        apply_groups._partition_groups(nodes, rels)
    )
    assert set(core_nodes) == {"module_surface"}
    assert set(analysis_nodes) == {"retirement_candidate", "complexity_candidate"}
    assert set(core_rels) == {"IMPORTS"}
    assert set(analysis_rels) == {"CANDIDATE_FOR_REMOVAL"}
    assert apply_groups._delete_managed_wave_batch_size(100) == 50
    assert apply_groups._analysis_node_batch_size(analysis_nodes, 20) == 5
    assert apply_groups._verification_sync_run(True, False, "run-1") == "run-1"
    assert apply_groups._verification_sync_run(False, False, "run-1") is None


def test_node_statement_groups_and_legacy_selection() -> None:
    snapshot = _core.GraphSnapshot()
    key = snapshot.add_node("module_surface", "src/example.py", role="kernel")
    grouped = apply_groups._node_statement_groups(snapshot, "run-1")
    assert list(grouped) == ["module_surface"]
    expected = _node_statement(snapshot.nodes[key], "run-1")
    assert grouped["module_surface"] == [expected]
    selection = apply_groups._selection_from_legacy_kwargs(
        {"only_labels": ["module_surface"], "only_analysis_layer": True}
    )
    assert selection.only_labels == ("module_surface",)
    assert selection.only_analysis_layer is True
    options = apply_groups._resolved_sync_apply_options(
        None, {"batch_size": 7, "prune_stale": True}
    )
    assert options == SyncApplyOptions(
        batch_size=7,
        prune_stale=True,
        full_reset_managed_wave=False,
        prune_legacy_unmanaged=False,
    )


def test_execute_prune_stale_statements_calls_client() -> None:
    client = MagicMock()
    apply_groups._execute_prune_stale_statements(client, "run-2")
    assert client.execute.call_count == 2
    first = client.execute.call_args_list[0].args[0][0]
    assert "DELETE r" in str(first["statement"])
    apply_groups._prune_managed_graph_if_requested(
        client,
        SyncApplyOptions(batch_size=10, prune_stale=False, prune_legacy_unmanaged=True),
        "run-2",
        ["module_surface"],
    )
    last = client.execute.call_args.args[0][0]
    assert "managed_labels" in last["parameters"]
