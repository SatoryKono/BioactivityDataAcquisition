# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# Governance checks for replay-critical wall-clock timestamp seams.

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TIME_SEAM_REGISTRY = ROOT / "configs/quality/time_seam_classification.yaml"
REPLAY_CRITICAL_FILES = (
    ROOT / "src/bioetl/application/core/lifecycle/checkpoint_manager.py",
    ROOT / "src/bioetl/application/composite/runner_pkg/runner_support_runtime.py",
    ROOT / "src/bioetl/infrastructure/checkpoint/local_checkpoint.py",
)
_APPLICATION_TIME_SEAM_CATEGORIES = frozenset(
    {"operator_time_allowed", "runtime_clock_adapter"}
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
            and func.attr == "time_ns"
            and isinstance(func.value, ast.Name)
            and func.value.id == "time"
        ):
            calls.append(("time.time_ns", node.lineno))
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "now"
            and isinstance(func.value, ast.Name)
            and func.value.id == "datetime"
        ):
            calls.append(("datetime.now", node.lineno))
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "utcnow"
            and isinstance(func.value, ast.Name)
            and func.value.id == "datetime"
        ):
            calls.append(("datetime.utcnow", node.lineno))
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
            and func.attr in {"time", "time_ns"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "time"
        ):
            owner = ".".join(self._scope) or "<module>"
            self.calls.append(f"{owner}:{node.lineno}:time.{func.attr}")
        self.generic_visit(node)


def _application_wall_clock_seams(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    visitor = _WallClockSeamVisitor(path)
    visitor.visit(tree)
    return visitor.calls


def _load_application_wall_clock_allowlist() -> dict[str, set[str]]:
    payload = yaml.safe_load(TIME_SEAM_REGISTRY.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    seams = payload.get("seams", [])
    assert isinstance(seams, list)

    allowlist: dict[str, set[str]] = {}
    for row in seams:
        assert isinstance(row, dict)
        path = row.get("path")
        call = row.get("call")
        scope = row.get("scope")
        category = row.get("category")
        replay_critical = row.get("replay_critical")
        if not (
            isinstance(path, str)
            and path.startswith("src/bioetl/application/")
            and call in {"datetime.now", "datetime.utcnow", "time.time", "time.time_ns"}
        ):
            continue
        assert isinstance(scope, str) and scope
        assert category in _APPLICATION_TIME_SEAM_CATEGORIES
        assert replay_critical is False
        allowlist.setdefault(path, set()).add(scope)
    return allowlist


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
        relative_path: {seam.split(":", maxsplit=1)[0] for seam in seams}
        for relative_path, seams in observed.items()
    }
    expected = {
        relative_path: set(functions)
        for relative_path, functions in _load_application_wall_clock_allowlist().items()
    }
    assert normalized == expected, (
        "Application wall-clock seams drifted. Inject ClockPort or explicit "
        f"timestamps for replay-adjacent paths; observed={observed!r}"
    )
