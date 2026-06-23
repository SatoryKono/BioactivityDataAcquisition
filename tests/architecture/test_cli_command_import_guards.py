"""Import guardrails for retained CLI compatibility seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.helpers.git_index_scan import git_tracked_files

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
CLI_ROOT = SRC_ROOT / "interfaces" / "cli"
PUBLIC_COMMAND_MODULES = {
    "adr",
    "archive",
    "checkpoint",
    "cleanup",
    "config",
    "config_dq",
    "diagnostics",
    "debug",
    "export",
    "health",
    "lineage",
    "lock",
    "maintenance",
    "plan",
    "quarantine",
    "run",
    "run_all",
    "run_composite",
    "run_manifest",
    "vacuum",
    "workflow",
}


def _iter_python_files(root: Path) -> list[Path]:
    return list(
        git_tracked_files(
            root=ROOT,
            paths=(root.relative_to(ROOT).as_posix(),),
            suffixes=(".py",),
        )
    )


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


@pytest.mark.architecture
def test_non_cli_source_avoids_interfaces_package_root_convenience_imports() -> None:
    """First-party source should import concrete interfaces directly."""
    violations: list[str] = []
    for path in _iter_python_files(SRC_ROOT):
        if path.is_relative_to(CLI_ROOT):
            continue
        imported_modules = _imported_modules(path)
        if "bioetl.interfaces" in imported_modules:
            violations.append(_relative(path))

    assert not violations, (
        "Non-CLI source must not import the bioetl.interfaces package root. "
        "Import bioetl.interfaces.cli or bioetl.interfaces.http directly:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_non_cli_source_keeps_retained_public_cli_seams_outside_runtime_code() -> None:
    """Retained public CLI command seams are for CLI wiring and tests only."""
    violations: list[str] = []
    allowed_prefix = "bioetl.interfaces.cli.commands."

    for path in _iter_python_files(SRC_ROOT):
        if path.is_relative_to(CLI_ROOT):
            continue
        imported_modules = _imported_modules(path)
        for module_name in imported_modules:
            if not module_name.startswith(allowed_prefix):
                continue
            suffix = module_name.removeprefix(allowed_prefix)
            if suffix.startswith("domains."):
                violations.append(f"{_relative(path)} -> {module_name}")
                continue
            if suffix in PUBLIC_COMMAND_MODULES:
                violations.append(f"{_relative(path)} -> {module_name}")

    assert not violations, (
        "Non-CLI source must not depend on retained public CLI command seams or "
        "their internal domain owners:\n" + "\n".join(violations)
    )
