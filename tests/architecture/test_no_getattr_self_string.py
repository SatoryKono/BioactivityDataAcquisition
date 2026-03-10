"""Architecture guard: forbid getattr(self, "...") in production code."""

from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path("src/bioetl")


def _find_getattr_self_string_calls(path: Path) -> list[tuple[int, str]]:
    """Return (line, attr_name) for getattr(self, "...") calls."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "getattr":
            continue
        if len(node.args) < 2:
            continue

        target = node.args[0]
        attr = node.args[1]
        if (
            isinstance(target, ast.Name)
            and target.id == "self"
            and isinstance(attr, ast.Constant)
            and isinstance(attr.value, str)
        ):
            violations.append((node.lineno, attr.value))

    return violations


def test_no_getattr_self_string_in_production_code() -> None:
    """Production code must use explicit typed contracts instead of dynamic self getattr."""
    violations: list[str] = []

    for py_file in SRC_ROOT.rglob("*.py"):
        file_violations = _find_getattr_self_string_calls(py_file)
        violations.extend(
            f"{py_file}:{line} -> getattr(self, {attr!r})"
            for line, attr in file_violations
        )

    assert not violations, (
        "Dynamic self attribute dispatch is forbidden in production code. "
        "Define a Protocol/ABC contract and call the method directly.\n"
        + "\n".join(sorted(violations))
    )
