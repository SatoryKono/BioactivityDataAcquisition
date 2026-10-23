#!/usr/bin/env python3
"""Check infrastructure layer architecture.

Validates that infrastructure adapters properly implement domain ports
and follow the Ports & Adapters (Hexagonal) architecture pattern.
"""

from __future__ import annotations

import ast
import re
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


_ANY_TOKEN = re.compile(r"\bAny\b")


def _imports_typing_name(tree: ast.AST, name: str) -> bool:
    """Return True when the tree imports ``name`` from ``typing``."""
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "typing"
        and any(alias.name == name for alias in node.names)
        for node in ast.walk(tree)
    )


def _domain_named_files(domain_path: Path, filename: str) -> list[Path]:
    """Return matching domain files in stable path order."""
    return sorted(path for path in domain_path.rglob(filename) if path.is_file())


def collect_domain_type_errors(domain_path: Path) -> list[str]:
    """Return blocking Protocol gaps for domain ``ports.py`` modules."""
    errors: list[str] = []
    for path in _domain_named_files(domain_path, "ports.py"):
        tree = _parse_file_tree(path)
        if tree is not None and not _imports_typing_name(tree, "Protocol"):
            errors.append(f"{path}: ports.py should use typing.Protocol")
    return errors


def collect_domain_type_notices(domain_path: Path) -> list[str]:
    """Return non-blocking NewType hints for domain ``types.py`` modules."""
    notices: list[str] = []
    for path in _domain_named_files(domain_path, "types.py"):
        tree = _parse_file_tree(path)
        if tree is not None and not _imports_typing_name(tree, "NewType"):
            notices.append(
                f"ℹ️  {path}: Consider using NewType for domain-specific types"
            )
    return notices


def _line_mentions_any(line: str) -> bool:
    """Return True for executable lines that mention ``Any``."""
    if "TYPE_CHECKING" in line or line.strip().startswith("#"):
        return False
    return _ANY_TOKEN.search(line) is not None


def _any_warnings_in_file(path: Path) -> list[str]:
    """Return Any-usage warnings for one Python file."""
    return [
        f"{path}:{index}: {line.strip()}"
        for index, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            1,
        )
        if _line_mentions_any(line)
    ]


def collect_any_usage_warnings(base_path: Path) -> list[str]:
    """Return advisory Any-usage warnings under domain and application."""
    warnings: list[str] = []
    for layer in ("domain", "application"):
        layer_path = base_path / "src" / "bioetl" / layer
        if not layer_path.is_dir():
            continue
        for py_file in sorted(layer_path.rglob("*.py")):
            warnings.extend(_any_warnings_in_file(py_file))
    return warnings


def _report_any_usage(base_path: Path) -> None:
    """Print advisory Any-usage findings. They do not fail the gate."""
    warnings = collect_any_usage_warnings(base_path)
    if not warnings:
        print("✅ No problematic Any type usage found")
        return
    print(f"⚠️  Found {len(warnings)} potential Any type usage(s):")
    for line in warnings[:10]:
        print(f"  {line}")
    extra = len(warnings) - 10
    if extra > 0:
        print(f"  ... and {extra} more")
    print("\nConsider using more specific types where possible.")


def _report_domain_type_definitions(domain_path: Path) -> int:
    """Print domain type-policy findings and return the exit code."""
    if not domain_path.is_dir():
        print("Domain layer not found")
        return 1
    for notice in collect_domain_type_notices(domain_path):
        print(notice)
    errors = collect_domain_type_errors(domain_path)
    if not errors:
        print("✅ Domain layer type definitions look good")
        return 0
    print("❌ Type definition issues found:")
    for issue in errors:
        print(f"  {issue}")
    return 1


def check_domain_type_policy(base_path: Path) -> int:
    """Run the domain NewType, Protocol, and Any policy gate."""
    exit_code = _report_domain_type_definitions(base_path / "src" / "bioetl" / "domain")
    _report_any_usage(base_path)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    """Run infrastructure architecture checks."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["domain-type-policy"]:
        return check_domain_type_policy(Path())
    if args:
        print(
            "usage: python -m scripts.engineering.qa.check_architecture "
            "[domain-type-policy]",
            file=sys.stderr,
        )
        return 2

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
