#!/usr/bin/env python3
"""Check application layer dependencies.

Ensures the application layer only imports from domain layer and does not
directly depend on infrastructure implementations.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

FORBIDDEN_PREFIXES = [
    "bioetl.infrastructure.adapters",
    "bioetl.infrastructure.storage",
    "bioetl.infrastructure.locking",
    "bioetl.infrastructure.checkpoint",
    "bioetl.infrastructure.quarantine",
]
ALLOWED_FILES: list[str] = []


def get_imports(filepath: Path) -> list[str]:
    """Extract all import statements from a Python file."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    return imports


def check_file(filepath: Path) -> list[str]:
    """Check a single file for forbidden imports."""
    if filepath.name in ALLOWED_FILES:
        return []

    violations: list[str] = []
    imports = get_imports(filepath)

    for imported_name in imports:
        for prefix in FORBIDDEN_PREFIXES:
            if imported_name.startswith(prefix):
                violations.append(f"{filepath}: forbidden import '{imported_name}'")

    return violations


def main() -> int:
    """Check all application layer files."""
    app_dir = Path("src/bioetl/application")
    if not app_dir.exists():
        print(f"Application directory not found: {app_dir}")
        return 1

    all_violations: list[str] = []
    for py_file in app_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        all_violations.extend(check_file(py_file))

    if all_violations:
        print("Architecture violations found:")
        for violation in all_violations:
            print(f"  - {violation}")
        return 1

    print("Application layer dependency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
