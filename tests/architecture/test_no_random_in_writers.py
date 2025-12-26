"""Architecture test: forbid random in storage writers."""
import ast
from pathlib import Path
import pytest

STORAGE_DIR = Path("src/bioetl/infrastructure/storage")
# Allowed exceptions (if any, currently none)
ALLOWED_RANDOM_FILES: set[str] = set()

def test_no_random_import_in_storage_writers():
    """Storage writers MUST NOT import random module.

    REQ-ARCH-030: Deterministic writes for reproducibility.
    See ADR-014 for rationale.
    """
    violations = []

    if not STORAGE_DIR.exists():
        pytest.skip(f"Directory {STORAGE_DIR} does not exist")

    for py_file in STORAGE_DIR.glob("*.py"):
        if py_file.name in ALLOWED_RANDOM_FILES:
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue # Skip non-text files if any

        try:
            tree = ast.parse(source)
        except SyntaxError:
            violations.append(f"{py_file.name}: SyntaxError parsing file")
            continue

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
        f"Random imports found in storage writers:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nStorage writers must be deterministic. "
        "See docs/02-architecture/decisions/ADR-014-deterministic-retries.md"
    )


def test_no_random_uniform_calls_in_storage():
    """Storage writers MUST NOT call random.uniform() directly."""
    violations = []

    if not STORAGE_DIR.exists():
        return

    for py_file in STORAGE_DIR.glob("*.py"):
        if py_file.name in ALLOWED_RANDOM_FILES:
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            continue

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
        f"random.uniform() calls found:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
