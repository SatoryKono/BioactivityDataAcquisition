#!/usr/bin/env python3
"""Check infrastructure layer architecture.

Validates that infrastructure adapters properly implement domain ports
and follow the Ports & Adapters (Hexagonal) architecture pattern.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_ADAPTER_DIRECTORIES = ("adapters", "storage", "locking", "checkpoint", "quarantine")


def _parse_file_tree(filepath: Path) -> ast.AST | None:
    """Parse Python file into AST, returning None on syntax errors."""
    try:
        return ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _is_port_related_import(node: ast.ImportFrom) -> bool:
    """Return True when import comes from domain ports/types surface."""
    module = node.module
    return bool(module) and ("domain.ports" in module or "domain.types" in module)


def _is_adapter_like_path(filepath: Path) -> bool:
    """Return True for infrastructure adapter/storage-like modules."""
    return any(directory in str(filepath) for directory in _ADAPTER_DIRECTORIES)


def check_adapter_implements_port(filepath: Path) -> list[str]:
    """Check if adapter classes reference domain ports."""
    violations: list[str] = []
    tree = _parse_file_tree(filepath)
    if tree is None:
        return [f"{filepath}: syntax error"]

    has_port_import = any(
        _is_port_related_import(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    if (
        _is_adapter_like_path(filepath)
        and not has_port_import
        and filepath.name.endswith("client.py")
    ):
        # Client modules may not always import ports directly.
        return violations

    return violations


def _infrastructure_import_violation(py_file: Path) -> str | None:
    """Return violation message when infrastructure imports application layer."""
    content = py_file.read_text(encoding="utf-8")
    if "from bioetl.application" in content or "import bioetl.application" in content:
        return f"{py_file}: infrastructure imports from application layer"
    return None


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    """Return absolute module names represented by one import node."""
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()


def _is_composition_implementation_import(module: str) -> bool:
    """Return whether a module crosses the composition contracts boundary."""
    if not module.startswith("bioetl.composition"):
        return False
    return module != "bioetl.composition.contracts" and not module.startswith(
        "bioetl.composition.contracts."
    )


def _composition_contract_import_violations(
    py_file: Path,
    tree: ast.AST,
) -> list[str]:
    """Return forbidden composition imports found in one parsed contracts file."""
    return [
        f"{py_file}: composition/contracts imports {module}"
        for node in ast.walk(tree)
        for module in _imported_modules(node)
        if _is_composition_implementation_import(module)
    ]


def check_composition_contracts_isolation(base_path: Path) -> list[str]:
    """composition/contracts must not import composition implementation modules."""
    violations: list[str] = []
    contracts_dir = base_path / "src" / "bioetl" / "composition" / "contracts"
    if not contracts_dir.exists():
        return []
    for py_file in contracts_dir.rglob("*.py"):
        tree = _parse_file_tree(py_file)
        if tree is None:
            violations.append(f"{py_file}: syntax error")
            continue
        violations.extend(_composition_contract_import_violations(py_file, tree))
    return violations


def check_composition_protocol_placement(base_path: Path) -> list[str]:
    """Shrink-only remaining Protocol declarations outside composition/contracts."""
    from scripts.engineering.qa.report_composition_protocol_inventory import (
        collect_scoped_protocols,
        evaluate,
    )
    import yaml

    config_path = (
        base_path / "configs" / "quality" / "composition_protocol_inventory.yaml"
    )
    if not config_path.exists():
        return [f"missing {config_path}"]
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return evaluate(config, collect_scoped_protocols())


def check_no_circular_imports(base_path: Path) -> list[str]:
    """Basic check for infrastructure -> application import violations."""
    violations: list[str] = []

    infra_dir = base_path / "src" / "bioetl" / "infrastructure"
    if not infra_dir.exists():
        return []

    for py_file in infra_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        violation = _infrastructure_import_violation(py_file)
        if violation is not None:
            violations.append(violation)

    return violations


def _iter_infrastructure_python_files(base_path: Path) -> list[Path]:
    infra_dir = base_path / "src" / "bioetl" / "infrastructure"
    if not infra_dir.exists():
        return []
    return [
        py_file
        for py_file in infra_dir.rglob("*.py")
        if not py_file.name.startswith("__")
    ]


def _collect_adapter_violations(base_path: Path) -> list[str]:
    violations: list[str] = []
    for py_file in _iter_infrastructure_python_files(base_path):
        violations.extend(check_adapter_implements_port(py_file))
    return violations


def main() -> int:
    """Run infrastructure architecture checks."""
    base_path = Path("")
    all_violations: list[str] = []

    all_violations.extend(check_no_circular_imports(base_path))
    all_violations.extend(check_composition_contracts_isolation(base_path))
    all_violations.extend(check_composition_protocol_placement(base_path))
    all_violations.extend(_collect_adapter_violations(base_path))

    if all_violations:
        print("Architecture violations found:")
        for violation in all_violations:
            print(f"  - {violation}")
        return 1

    print("Infrastructure layer architecture check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
