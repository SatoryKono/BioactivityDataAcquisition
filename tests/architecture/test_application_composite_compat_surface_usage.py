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
            "merger_compat_mixin",
        }
    ),
}
ALLOWED_SRC_IMPORTS = {
    "bioetl.application.composite.merger_compat_mixin": frozenset(
        {
            ROOT / "src" / "bioetl" / "application" / "composite" / "merger.py",
        }
    ),
}
ALLOWED_TEST_IMPORTS = {
    "bioetl.application.composite.merger_compat_mixin": frozenset(),
}
REMOVED_COMPAT_MODULES = frozenset(
    {
        "bioetl.application.composite.join_planner_compat_mixin",
        "bioetl.application.composite.runner",
    }
)
REMOVED_COMPAT_PARENT_IMPORTS = {
    "bioetl.application.composite": frozenset(
        {
            "join_planner_compat_mixin",
            "runner",
        }
    )
}
REMOVED_COMPAT_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "composite"
        / "join_planner_compat_mixin.py",
        ROOT / "src" / "bioetl" / "application" / "composite" / "runner.py",
    }
)


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


def _iter_removed_import_records(search_root: Path) -> list[tuple[Path, int, str]]:
    records: list[tuple[Path, int, str]] = []
    for py_file in search_root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in REMOVED_COMPAT_MODULES:
                records.append((py_file, node.lineno, node.module))
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module in REMOVED_COMPAT_PARENT_IMPORTS
            ):
                removed_children = REMOVED_COMPAT_PARENT_IMPORTS[node.module]
                for alias in node.names:
                    if alias.name in removed_children:
                        records.append(
                            (
                                py_file,
                                node.lineno,
                                f"{node.module}.{alias.name}",
                            )
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in REMOVED_COMPAT_MODULES:
                        records.append((py_file, node.lineno, alias.name))
    return records


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


@pytest.mark.architecture
def test_removed_application_composite_runner_facade_file_stays_absent() -> None:
    """Removed application.composite compat shims should stay absent."""
    lingering = sorted(
        path.relative_to(ROOT).as_posix()
        for path in REMOVED_COMPAT_FILES
        if path.exists()
    )
    assert not lingering, (
        "Removed application.composite compat shims must stay absent:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_removed_application_composite_runner_facade_is_not_imported() -> None:
    """Removed application.composite compat shims must not be imported."""
    records = _iter_removed_import_records(SRC_ROOT)
    records.extend(_iter_removed_import_records(TESTS_ROOT))
    violations = [
        f"{py_file.relative_to(ROOT).as_posix()}:{lineno} imports {module_name}"
        for py_file, lineno, module_name in records
    ]
    assert not violations, (
        "Removed application.composite compat shims must stay absent from imports:\n"
        + "\n".join(violations)
    )
