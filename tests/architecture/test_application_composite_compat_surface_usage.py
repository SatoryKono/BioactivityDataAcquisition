"""Guardrails for application.composite compatibility surfaces."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
COMPAT_PARENT_IMPORTS = {
    "bioetl.application.composite": frozenset(
        {
            "join_planner_compat_mixin",
            "merger_compat_mixin",
            "runner",
        }
    ),
}
ALLOWED_SRC_IMPORTS = {
    "bioetl.application.composite.join_planner_compat_mixin": frozenset(
        {
            ROOT / "src" / "bioetl" / "application" / "composite" / "join_planner.py",
        }
    ),
    "bioetl.application.composite.merger_compat_mixin": frozenset(
        {
            ROOT / "src" / "bioetl" / "application" / "composite" / "merger.py",
        }
    ),
    "bioetl.application.composite.runner": frozenset(),
}
ALLOWED_TEST_IMPORTS = {
    "bioetl.application.composite.join_planner_compat_mixin": frozenset(),
    "bioetl.application.composite.merger_compat_mixin": frozenset(),
    "bioetl.application.composite.runner": frozenset(
        {
            ROOT
            / "tests"
            / "unit"
            / "application"
            / "composite"
            / "test_runner_root_facade_reexport.py",
        }
    ),
}


def _iter_import_records(search_root: Path) -> list[tuple[Path, int, str]]:
    records: list[tuple[Path, int, str]] = []
    for py_file in search_root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in ALLOWED_SRC_IMPORTS:
                records.append((py_file, node.lineno, node.module))
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module in COMPAT_PARENT_IMPORTS
            ):
                compat_children = COMPAT_PARENT_IMPORTS[node.module]
                for alias in node.names:
                    if alias.name in compat_children:
                        records.append(
                            (
                                py_file,
                                node.lineno,
                                f"{node.module}.{alias.name}",
                            )
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ALLOWED_SRC_IMPORTS:
                        records.append((py_file, node.lineno, alias.name))
    return records


def _format_violations(
    records: list[tuple[Path, int, str]],
    *,
    allowed_imports: dict[str, frozenset[Path]],
) -> list[str]:
    violations: list[str] = []
    for py_file, lineno, module_name in records:
        if py_file in allowed_imports[module_name]:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        violations.append(f"{rel_path}:{lineno} imports {module_name}")
    return violations


@pytest.mark.architecture
def test_application_composite_compat_surfaces_are_confined_in_src() -> None:
    """First-party src must not grow new imports of composite compatibility modules."""
    violations = _format_violations(
        _iter_import_records(SRC_ROOT),
        allowed_imports=ALLOWED_SRC_IMPORTS,
    )
    assert not violations, (
        "application.composite compatibility surfaces leaked beyond allowed src files:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_application_composite_compat_surfaces_are_confined_in_tests() -> None:
    """Ordinary tests must not accumulate new imports of composite compatibility modules."""
    violations = _format_violations(
        _iter_import_records(TESTS_ROOT),
        allowed_imports=ALLOWED_TEST_IMPORTS,
    )
    assert not violations, (
        "application.composite compatibility surfaces gained new non-smoke test imports:\n"
        + "\n".join(violations)
    )
