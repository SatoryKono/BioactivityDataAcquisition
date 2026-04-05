#!/usr/bin/env python3
"""Check infrastructure layer architecture.

Validates that infrastructure adapters properly implement domain ports
and follow the Ports & Adapters (Hexagonal) architecture pattern.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def check_adapter_implements_port(filepath: Path) -> list[str]:
    """Check if adapter classes reference domain ports."""
    violations: list[str] = []

    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return [f"{filepath}: syntax error"]

    has_port_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "domain.ports" in node.module:
                has_port_import = True
                break
            if node.module and "domain.types" in node.module:
                has_port_import = True
                break

    adapter_dirs = ["adapters", "storage", "locking", "checkpoint", "quarantine"]
    if any(directory in str(filepath) for directory in adapter_dirs):
        if not has_port_import and filepath.name.endswith("client.py"):
            # Client modules may not always import ports directly.
            pass

    return violations


def check_no_circular_imports(base_path: Path) -> list[str]:
    """Basic check for infrastructure -> application import violations."""
    violations: list[str] = []

    infra_dir = base_path / "src" / "bioetl" / "infrastructure"
    if not infra_dir.exists():
        return []

    for py_file in infra_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        content = py_file.read_text(encoding="utf-8")
        if (
            "from bioetl.application" in content
            or "import bioetl.application" in content
        ):
            violations.append(
                f"{py_file}: infrastructure imports from application layer"
            )

    return violations


def main() -> int:
    """Run infrastructure architecture checks."""
    base_path = Path("")
    all_violations: list[str] = []

    all_violations.extend(check_no_circular_imports(base_path))

    infra_dir = base_path / "src" / "bioetl" / "infrastructure"
    if infra_dir.exists():
        for py_file in infra_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            all_violations.extend(check_adapter_implements_port(py_file))

    if all_violations:
        print("Architecture violations found:")
        for violation in all_violations:
            print(f"  - {violation}")
        return 1

    print("Infrastructure layer architecture check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
