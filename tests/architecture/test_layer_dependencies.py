import ast
from pathlib import Path

import pytest


DOMAIN_ROOT = Path("src/bioetl/domain")
FORBIDDEN_ABSOLUTE_PREFIXES: tuple[str, ...] = ("bioetl.infrastructure",)
FORBIDDEN_RELATIVE_PREFIXES: tuple[str, ...] = ("infrastructure",)


def _is_forbidden_absolute(candidate: str) -> bool:
    return any(
        candidate == prefix or candidate.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_ABSOLUTE_PREFIXES
    )


def _is_forbidden_relative(candidate: str) -> bool:
    return any(
        candidate == prefix or candidate.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_RELATIVE_PREFIXES
    )


def _format_violation(path: Path, lineno: int, reference: str) -> str:
    rel_path = path.as_posix()
    return f"{rel_path}:{lineno}: forbidden import {reference}"


def _collect_import_violations(path: Path) -> list[str]:
    code = path.read_text(encoding="utf-8")
    tree = ast.parse(code)
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(_violations_for_import(node, path))
        elif isinstance(node, ast.ImportFrom):
            violations.extend(_violations_for_import_from(node, path))

    return violations


def _violations_for_import(node: ast.Import, path: Path) -> list[str]:
    return [
        _format_violation(path, node.lineno, alias.name)
        for alias in node.names
        if _is_forbidden_absolute(alias.name)
    ]


def _violations_for_import_from(node: ast.ImportFrom, path: Path) -> list[str]:
    module = node.module or ""
    violations: list[str] = []
    violations.extend(
        _module_import_violations(path, node.lineno, module, is_relative=node.level > 0)
    )
    violations.extend(
        _relative_alias_violations(
            path, node, module, has_relative_prefix=node.level > 0
        )
    )
    violations.extend(
        _alias_violations(
            path, node, module=module, is_relative=node.level > 0
        )
    )
    return violations


def _module_import_violations(
    path: Path, lineno: int, module: str, *, is_relative: bool
) -> list[str]:
    violations: list[str] = []
    if module and _is_forbidden_absolute(module):
        violations.append(_format_violation(path, lineno, module))
    if is_relative and module and _is_forbidden_relative(module):
        violations.append(_format_violation(path, lineno, module))
    return violations


def _relative_alias_violations(
    path: Path, node: ast.ImportFrom, module: str, *, has_relative_prefix: bool
) -> list[str]:
    if not has_relative_prefix or module:
        return []
    return [
        _format_violation(path, node.lineno, alias.name)
        for alias in node.names
        if _is_forbidden_relative(alias.name)
    ]


def _alias_violations(
    path: Path, node: ast.ImportFrom, *, module: str, is_relative: bool
) -> list[str]:
    violations: list[str] = []
    for alias in node.names:
        qualified = f"{module}.{alias.name}" if module else alias.name
        if _is_forbidden_absolute(qualified):
            violations.append(_format_violation(path, node.lineno, qualified))
        if is_relative and _is_forbidden_relative(qualified):
            violations.append(_format_violation(path, node.lineno, qualified))
    return violations


def test_domain_does_not_depend_on_infrastructure() -> None:
    violations: list[str] = []
    for file_path in sorted(DOMAIN_ROOT.rglob("*.py")):
        violations.extend(_collect_import_violations(file_path))

    if violations:
        formatted = "\n".join(sorted(set(violations)))
        pytest.fail(f"Forbidden imports detected:\n{formatted}")

