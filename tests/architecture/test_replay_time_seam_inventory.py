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
APPLICATION_WALL_CLOCK_ALLOWLIST: dict[str, dict[str, str]] = {
    "src/bioetl/application/runtime_clock.py": {
        "RuntimeClockService.now": "ClockPort implementation seam",
    },
    "src/bioetl/application/services/debug_export_helpers.py": {
        "_utc_now": "operator debug-export default created_at factory",
    },
    "src/bioetl/application/services/export_manifest_identity.py": {
        "utc_now": "operator-only export manifest timestamp fallback",
    },
}

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


class _WallClockSeamVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self._scope: list[str] = []
        self.calls: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"now", "utcnow"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "datetime"
        ):
            owner = ".".join(self._scope) or "<module>"
            self.calls.append(f"{owner}:{node.lineno}:datetime.{func.attr}")
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "time"
            and isinstance(func.value, ast.Name)
            and func.value.id == "time"
        ):
            owner = ".".join(self._scope) or "<module>"
            self.calls.append(f"{owner}:{node.lineno}:time.time")
        self.generic_visit(node)


def _application_wall_clock_seams(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    visitor = _WallClockSeamVisitor(path)
    visitor.visit(tree)
    return visitor.calls


def test_replay_critical_checkpoint_surfaces_do_not_call_wall_clock_directly() -> None:
    violations = {
        path.relative_to(ROOT).as_posix(): _forbidden_wall_clock_calls(path)
        for path in REPLAY_CRITICAL_FILES
    }
    violations = {path: calls for path, calls in violations.items() if calls}

    assert violations == {}


def test_application_wall_clock_seams_are_classified_and_bounded() -> None:
    """Debug/export wall-clock seams must stay explicit and non-replay-critical."""
    observed: dict[str, list[str]] = {}
    for path in sorted((ROOT / "src/bioetl/application").rglob("*.py")):
        seams = _application_wall_clock_seams(path)
        if seams:
            observed[path.relative_to(ROOT).as_posix()] = seams

    normalized = {
        relative_path: {
            seam.split(":", maxsplit=1)[0]
            for seam in seams
        }
        for relative_path, seams in observed.items()
    }
    expected = {
        relative_path: set(functions)
        for relative_path, functions in APPLICATION_WALL_CLOCK_ALLOWLIST.items()
    }
    assert normalized == expected, (
        "Application wall-clock seams drifted. Inject ClockPort or explicit "
        f"timestamps for replay-adjacent paths; observed={observed!r}"
    )
