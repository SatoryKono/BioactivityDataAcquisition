"""Ratchet and unit coverage for AUD-002 post-apply verification extract (#10526)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import apply_verify

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
VERIFY = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "apply_verify.py"
# Line count on origin/main after the apply-groups slice (#10648).
_CORE_LOC_BEFORE_VERIFY_SLICE = 16404


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_apply_verify_owns_helpers_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    verify_text = VERIFY.read_text(encoding="utf-8")
    assert "def _retry_critical_analysis_groups(" not in core_text
    assert "def _verify_expected_group_counts(" not in core_text
    assert callable(_core._verify_sync_snapshot)
    assert "def _retry_critical_analysis_groups(" in verify_text
    assert (
        _core._verify_expected_group_counts
        is apply_verify._verify_expected_group_counts
    )
    assert (
        _core.CRITICAL_ANALYSIS_NODE_LABELS
        is apply_verify.CRITICAL_ANALYSIS_NODE_LABELS
    )
    assert _loc(CORE) < _CORE_LOC_BEFORE_VERIFY_SLICE
    assert _loc(VERIFY) < 500


def test_group_name_and_mismatch_helpers() -> None:
    groups = {
        "retirement_candidate": [{}, {}],
        "complexity_candidate": [{}],
    }
    assert apply_verify._active_group_names(
        apply_verify.CRITICAL_ANALYSIS_NODE_LABELS, groups
    ) == ["retirement_candidate", "complexity_candidate"]
    assert apply_verify._missing_group_names(
        ["retirement_candidate", "complexity_candidate"],
        groups,
        {"retirement_candidate": 2, "complexity_candidate": 0},
    ) == ["complexity_candidate"]
    mismatches = apply_verify._group_count_mismatches(
        grouped_statements=groups,
        live_counts={"retirement_candidate": 2, "complexity_candidate": 0},
        noun="label",
    )
    assert mismatches == ["label `complexity_candidate` expected 1, live managed 0"]
    apply_verify._raise_analysis_group_mismatches([], prefix="x")
    with pytest.raises(RuntimeError, match="prefix"):
        apply_verify._raise_analysis_group_mismatches(["a"], prefix="prefix: ")


def test_retry_missing_groups_skips_empty_and_executes_named() -> None:
    client = MagicMock()
    apply_verify._retry_missing_groups(client, {"a": [{}]}, [], 2, kind="node")
    client.execute.assert_not_called()
    apply_verify._retry_missing_groups(
        client,
        {"a": [{"statement": "A"}], "b": [{"statement": "B"}]},
        ["b"],
        1,
        kind="node",
    )
    executed = [call.args[0] for call in client.execute.call_args_list]
    assert executed == [[{"statement": "B"}]]


def test_verify_expected_group_counts_raises_on_mismatch() -> None:
    client = MagicMock()
    client.query.side_effect = [
        [{"label": "module_surface", "count": 0}],
        [{"relation_type": "IMPORTS", "count": 1}],
    ]
    with pytest.raises(RuntimeError, match="targeted sync groups"):
        apply_verify._verify_expected_group_counts(
            client,
            {"module_surface": [{}, {}]},
            {"IMPORTS": [{}]},
            strict_analysis=False,
            sync_run="run-1",
        )
