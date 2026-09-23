"""Ratchet and unit coverage for AUD-002 CLI leftovers and apply batch extract (#10526)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import _core_cli
from memory.graph.sync_pkg import apply_runtime
from memory.graph.sync_pkg._core_models import GroupedStatementFailureContext

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
CLI_MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core_cli.py"
APPLY_MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "apply_runtime.py"
# Line count on origin/main after the Cypher slice (#10640).
_CORE_LOC_BEFORE_CLI_APPLY_SLICE = 17146


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_cli_leftovers_and_apply_batch_leave_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    cli_text = CLI_MOD.read_text(encoding="utf-8")
    apply_text = APPLY_MOD.read_text(encoding="utf-8")
    assert "import argparse" not in core_text
    assert "def _selection_from_args(" not in core_text
    assert "def _execute_statement_batch(" not in core_text
    assert "def _selection_from_args(" in cli_text
    assert "def _execute_statement_batch(" in apply_text
    assert _core._selection_from_args is _core_cli._selection_from_args
    assert (
        _core._execute_grouped_statements is apply_runtime._execute_grouped_statements
    )
    assert _loc(CORE) < _CORE_LOC_BEFORE_CLI_APPLY_SLICE
    assert _loc(CLI_MOD) < 500
    assert _loc(APPLY_MOD) < 500


def test_batched_and_failure_context() -> None:
    assert apply_runtime._batched([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    named = apply_runtime._statement_failure_context(
        {"parameters": {"name": "src/example.py"}}
    )
    assert named == "name='src/example.py'"
    edge = apply_runtime._statement_failure_context(
        {"parameters": {"source_name": "a", "target_name": "b"}}
    )
    assert edge == "source='a', target='b'"


def test_execute_grouped_statements_calls_client_in_sorted_batches() -> None:
    client = MagicMock()
    apply_runtime._execute_grouped_statements(
        client,
        {
            "beta": [{"statement": "B2"}, {"statement": "B1"}],
            "alpha": [{"statement": "A"}],
        },
        batch_size=1,
        kind="node",
    )
    executed = [call.args[0] for call in client.execute.call_args_list]
    assert executed == [
        [{"statement": "A"}],
        [{"statement": "B2"}],
        [{"statement": "B1"}],
    ]


def test_raise_grouped_statement_failure_includes_context() -> None:
    with pytest.raises(RuntimeError, match="group `labels`"):
        apply_runtime._raise_grouped_statement_failure(
            GroupedStatementFailureContext(
                kind="node",
                group_name="labels",
                batch_index=1,
                batch_count=2,
                statement_index=1,
                statement_count=1,
            ),
            statement={"parameters": {"name": "n1"}},
            cause=RuntimeError("boom"),
        )


def test_selection_from_args_reexport_matches_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent = SimpleNamespace(only_labels=("module_surface",))
    monkeypatch.setattr(
        "memory.graph.sync_pkg.cli._selection_from_args",
        lambda args: ("ok", args.only_labels),
    )
    assert _core_cli._selection_from_args(sent) == ("ok", ("module_surface",))
