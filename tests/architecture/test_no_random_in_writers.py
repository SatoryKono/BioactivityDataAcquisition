"""Architecture test: запрет random в storage writers.

REQ-ARCH-030: Deterministic writes for reproducibility.
See docs/02-architecture/decisions/ADR-014-deterministic-writes.md
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

# Path relative to project root
STORAGE_DIR = Path("src/bioetl/infrastructure/storage")

# Files explicitly allowed to use random (should be empty for storage writers)
ALLOWED_RANDOM_FILES: set[str] = set()


def _storage_base_dir() -> Path:
    if STORAGE_DIR.exists():
        return STORAGE_DIR
    return Path(__file__).parent.parent.parent / STORAGE_DIR


def _parsed_tree(py_file: Path) -> ast.AST:
    return ast.parse(py_file.read_text(encoding="utf-8"))


def _collect_storage_python_files(base: Path) -> list[Path]:
    """Collect all first-party Python files below the storage package."""
    return sorted(base.rglob("*.py"))


def _storage_relative_path(py_file: Path) -> str:
    try:
        return py_file.relative_to(_storage_base_dir()).as_posix()
    except ValueError:
        return py_file.as_posix()


def _is_allowed_random_file(py_file: Path) -> bool:
    return _storage_relative_path(py_file) in ALLOWED_RANDOM_FILES


def _random_import_violations(py_file: Path) -> list[str]:
    violations: list[str] = []
    relative_path = _storage_relative_path(py_file)
    for node in ast.walk(_parsed_tree(py_file)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random":
                    violations.append(f"{relative_path}:{node.lineno}: import random")
        elif isinstance(node, ast.ImportFrom) and node.module == "random":
            violations.append(f"{relative_path}:{node.lineno}: from random import ...")
    return violations


def _random_call_violations(py_file: Path, method_name: str) -> list[str]:
    violations: list[str] = []
    relative_path = _storage_relative_path(py_file)
    for node in ast.walk(_parsed_tree(py_file)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != method_name:
            continue
        if isinstance(node.func.value, ast.Name) and node.func.value.id == "random":
            violations.append(f"{relative_path}:{node.lineno}: random.{method_name}()")
    return violations


def test_collect_storage_python_files_includes_nested_packages(tmp_path: Path) -> None:
    nested_file = tmp_path / "silver" / "runtime_helpers.py"
    nested_file.parent.mkdir()
    nested_file.write_text("# nested storage helper\n", encoding="utf-8")

    collected = _collect_storage_python_files(tmp_path)

    assert nested_file in collected


class TestNoRandomInStorageWriters:
    """Tests ensuring storage writers don't use random module."""

    @pytest.fixture
    def storage_python_files(self) -> list[Path]:
        """Get all Python files in the storage package tree."""
        return _collect_storage_python_files(_storage_base_dir())

    def test_no_random_import_in_storage_writers(
        self, storage_python_files: list[Path]
    ) -> None:
        """Storage writers MUST NOT import random module.

        Random introduces non-determinism which breaks reproducibility.
        Use fixed values or hash-based deterministic alternatives.
        """
        violations = []

        for py_file in storage_python_files:
            if _is_allowed_random_file(py_file):
                continue
            violations.extend(_random_import_violations(py_file))

        assert not violations, (
            "Random imports found in storage writers:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nStorage writers must be deterministic. "
            "See docs/02-architecture/decisions/ADR-014-deterministic-writes.md"
        )

    def test_no_random_uniform_calls_in_storage(
        self, storage_python_files: list[Path]
    ) -> None:
        """Storage writers MUST NOT call random.uniform() directly."""
        violations = []

        for py_file in storage_python_files:
            if _is_allowed_random_file(py_file):
                continue
            violations.extend(_random_call_violations(py_file, "uniform"))

        assert not violations, (
            "random.uniform() calls found:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nUse fixed delay values instead of random for determinism."
        )

    def test_no_random_choice_calls_in_storage(
        self, storage_python_files: list[Path]
    ) -> None:
        """Storage writers MUST NOT call random.choice() directly."""
        violations = []

        for py_file in storage_python_files:
            if _is_allowed_random_file(py_file):
                continue
            violations.extend(_random_call_violations(py_file, "choice"))

        assert not violations, "random.choice() calls found:\n" + "\n".join(
            f"  - {v}" for v in violations
        )
