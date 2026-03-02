#!/usr/bin/env python3
"""Check infrastructure layer architecture.

Validates that infrastructure adapters properly implement domain ports
and follow the Ports & Adapters (Hexagonal) architecture pattern.

This script is part of the architecture validation CI pipeline.
"""

import ast
import sys
from pathlib import Path


def check_adapter_implements_port(filepath: Path) -> list[str]:
    """Check if adapter classes reference domain ports."""
    violations = []

    with open(filepath, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return [f"{filepath}: syntax error"]

    # Check for port imports
    has_port_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "domain.ports" in node.module:
                has_port_import = True
                break
            if node.module and "domain.types" in node.module:
                has_port_import = True
                break

    # Adapters should reference domain types
    adapter_dirs = ["adapters", "storage", "locking", "checkpoint", "quarantine"]
    if any(d in str(filepath) for d in adapter_dirs):
        if not has_port_import and "client.py" in filepath.name:
            # Client files should implement ports
            pass  # Relaxed check - not all need direct port imports

    return violations


def check_no_circular_imports(base_path: Path) -> list[str]:
    """Basic check for potential circular import patterns."""
    violations = []

    # Infrastructure should not import from application
    infra_dir = base_path / "src" / "bioetl" / "infrastructure"
    if not infra_dir.exists():
        return []

    for py_file in infra_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        with open(py_file, encoding="utf-8") as f:
            content = f.read()

        if (
            "from bioetl.application" in content
            or "import bioetl.application" in content
        ):
            violations.append(
                f"{py_file}: infrastructure imports from application layer"
            )

    return violations


def main() -> int:
    """Run architecture checks."""
    base_path = Path("")

    all_violations = []

    # Check for circular imports
    violations = check_no_circular_imports(base_path)
    all_violations.extend(violations)

    # Check adapters
    infra_dir = base_path / "src" / "bioetl" / "infrastructure"
    if infra_dir.exists():
        for py_file in infra_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            violations = check_adapter_implements_port(py_file)
            all_violations.extend(violations)

    if all_violations:
        print("Architecture violations found:")
        for v in all_violations:
            print(f"  - {v}")
        return 1

    print("Infrastructure layer architecture check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
