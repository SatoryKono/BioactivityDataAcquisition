#!/usr/bin/env python3
"""Check application layer dependencies.

Ensures the application layer only imports from domain layer
and does not directly depend on infrastructure implementations.

This script is part of the architecture validation CI pipeline.
"""

import ast
import sys
from pathlib import Path

# Forbidden imports in application layer
FORBIDDEN_PREFIXES = [
    "bioetl.infrastructure.adapters",
    "bioetl.infrastructure.storage",
    "bioetl.infrastructure.locking",
    "bioetl.infrastructure.checkpoint",
    "bioetl.infrastructure.quarantine",
]

# Allowed exceptions (factory classes that wire up dependencies)
# NOTE: Empty list - all application layer files must follow architecture rules
ALLOWED_FILES: list[str] = []


def get_imports(filepath: Path) -> list[str]:
    """Extract all import statements from a Python file."""
    with open(filepath, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return imports


def check_file(filepath: Path) -> list[str]:
    """Check a single file for forbidden imports."""
    if filepath.name in ALLOWED_FILES:
        return []

    violations = []
    imports = get_imports(filepath)

    for imp in imports:
        for prefix in FORBIDDEN_PREFIXES:
            if imp.startswith(prefix):
                violations.append(f"{filepath}: forbidden import '{imp}'")

    return violations


def main() -> int:
    """Check all application layer files."""
    app_dir = Path("src/bioetl/application")

    if not app_dir.exists():
        print(f"Application directory not found: {app_dir}")
        return 1

    all_violations = []

    for py_file in app_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        violations = check_file(py_file)
        all_violations.extend(violations)

    if all_violations:
        print("Architecture violations found:")
        for v in all_violations:
            print(f"  - {v}")
        return 1

    print("Application layer dependency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
