# Governance checks for replay-critical wall-clock timestamp seams.

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPLAY_CRITICAL_FILES = (
    ROOT / "src/bioetl/application/core/lifecycle/checkpoint_manager.py",
    ROOT / "src/bioetl/application/composite/runner_pkg/runner_support_runtime.py",
    ROOT / "src/bioetl/infrastructure/checkpoint/local_checkpoint.py",
)

pytestmark = pytest.mark.architecture


def _forbidden_wall_clock_calls(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "time"
            and isinstance(func.value, ast.Name)
            and func.value.id == "time"
        ):
            calls.append(("time.time", node.lineno))
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "now"
            and isinstance(func.value, ast.Name)
            and func.value.id == "datetime"
        ):
            calls.append(("datetime.now", node.lineno))
    return calls


def test_replay_critical_checkpoint_surfaces_do_not_call_wall_clock_directly() -> None:
    violations = {
        path.relative_to(ROOT).as_posix(): _forbidden_wall_clock_calls(path)
        for path in REPLAY_CRITICAL_FILES
    }
    violations = {path: calls for path, calls in violations.items() if calls}

    assert violations == {}
