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
"""Architecture guards for classified wall-clock seams."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "configs" / "quality" / "time_seam_classification.yaml"
ALLOWED_CATEGORIES = {
    "operator_time_allowed",
    "runtime_clock_adapter",
    "replay_time_forbidden",
}


@dataclass(frozen=True, order=True)
class WallClockCall:
    path: str
    scope: str
    call: str


class _WallClockVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.scope: list[str] = []
        self.calls: list[WallClockCall] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _wall_clock_call_name(node)
        if call_name is not None:
            self.calls.append(
                WallClockCall(
                    path=self.path.relative_to(ROOT).as_posix(),
                    scope=".".join(self.scope) or "<module>",
                    call=call_name,
                )
            )
        self.generic_visit(node)


def _wall_clock_call_name(node: ast.Call) -> str | None:
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    if (
        func.attr in {"now", "utcnow"}
        and isinstance(func.value, ast.Name)
        and func.value.id == "datetime"
    ):
        return f"datetime.{func.attr}"
    if (
        func.attr == "today"
        and isinstance(func.value, ast.Name)
        and func.value.id == "date"
    ):
        return "date.today"
    if (
        func.attr in {"time", "time_ns"}
        and isinstance(func.value, ast.Name)
        and func.value.id == "time"
    ):
        return f"time.{func.attr}"
    return None


def _observed_calls() -> list[WallClockCall]:
    calls: list[WallClockCall] = []
    source_paths = [
        *sorted((ROOT / "src" / "bioetl").rglob("*.py")),
        ROOT / "src" / "memory" / "tooling" / "prune.py",
        ROOT / "src" / "memory" / "tooling" / "review_curated.py",
    ]
    for path in source_paths:
        visitor = _WallClockVisitor(path)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
        calls.extend(visitor.calls)
    return sorted(calls)


def _load_registry() -> dict[str, Any]:
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "time seam registry must be a mapping"
    return payload


def _registered_calls(payload: dict[str, Any]) -> list[WallClockCall]:
    seams = payload.get("seams")
    assert isinstance(seams, list) and seams, "time seam registry must declare seams"
    calls: list[WallClockCall] = []
    for seam in seams:
        assert isinstance(seam, dict), "time seam entries must be mappings"
        category = seam.get("category")
        assert category in ALLOWED_CATEGORIES, f"unknown seam category: {category!r}"
        assert isinstance(seam.get("rationale"), str) and seam["rationale"].strip()
        assert seam.get("replay_critical") is False, (
            "Direct wall-clock seams cannot be classified as replay-critical; "
            "inject ClockPort or explicit timestamp parameters instead."
        )
        calls.append(
            WallClockCall(
                path=str(seam["path"]),
                scope=str(seam["scope"]),
                call=str(seam["call"]),
            )
        )
    return sorted(calls)


def test_all_direct_wall_clock_calls_are_classified() -> None:
    """Every direct wall-clock call must have an explicit owner/category."""
    payload = _load_registry()

    assert set(payload["allowed_categories"]) == ALLOWED_CATEGORIES
    assert _observed_calls() == _registered_calls(payload)


def test_replay_time_forbidden_has_no_active_source_seams() -> None:
    """Replay-critical paths must fail closed instead of registering exceptions."""
    payload = _load_registry()
    forbidden = [
        seam
        for seam in payload["seams"]
        if isinstance(seam, dict) and seam.get("category") == "replay_time_forbidden"
    ]

    assert forbidden == []
