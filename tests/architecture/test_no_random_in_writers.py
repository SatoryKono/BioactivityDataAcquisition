"""Architecture test: запрет random в storage writers.

REQ-ARCH-030: Deterministic writes for reproducibility.
See docs/02-architecture/decisions/ADR-014-deterministic-writes.md
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Path relative to project root
STORAGE_DIR = Path("src/bioetl/infrastructure/storage")

# Files explicitly allowed to use random (should be empty for storage writers)
ALLOWED_RANDOM_FILES: set[str] = set()


class TestNoRandomInStorageWriters:
    """Tests ensuring storage writers don't use random module."""

    @pytest.fixture
    def storage_python_files(self) -> list[Path]:
        """Get all Python files in storage directory."""
        # Handle both running from project root and tests directory
        if STORAGE_DIR.exists():
            base = STORAGE_DIR
        else:
            base = Path(__file__).parent.parent.parent / STORAGE_DIR
        return list(base.glob("*.py"))

    def test_no_random_import_in_storage_writers(
        self, storage_python_files: list[Path]
    ) -> None:
        """Storage writers MUST NOT import random module.

        Random introduces non-determinism which breaks reproducibility.
        Use fixed values or hash-based deterministic alternatives.
        """
        violations = []

        for py_file in storage_python_files:
            if py_file.name in ALLOWED_RANDOM_FILES:
                continue

            source = py_file.read_text()
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "random":
                            violations.append(
                                f"{py_file.name}:{node.lineno}: import random"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module == "random":
                        violations.append(
                            f"{py_file.name}:{node.lineno}: from random import ..."
                        )

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
            if py_file.name in ALLOWED_RANDOM_FILES:
                continue

            source = py_file.read_text()
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr == "uniform":
                            if isinstance(node.func.value, ast.Name):
                                if node.func.value.id == "random":
                                    violations.append(
                                        f"{py_file.name}:{node.lineno}: random.uniform()"
                                    )

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
            if py_file.name in ALLOWED_RANDOM_FILES:
                continue

            source = py_file.read_text()
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr == "choice":
                            if isinstance(node.func.value, ast.Name):
                                if node.func.value.id == "random":
                                    violations.append(
                                        f"{py_file.name}:{node.lineno}: random.choice()"
                                    )

        assert not violations, (
            "random.choice() calls found:\n" + "\n".join(f"  - {v}" for v in violations)
        )
