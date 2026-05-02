"""Guardrails for deprecated symbols on ``bioetl.composition.entrypoints``."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
ENTRYPOINTS_MODULE = "bioetl.composition.entrypoints"
ENTRYPOINTS_FILE = SRC_ROOT / "composition" / "entrypoints.py"


def _legacy_entrypoint_symbols() -> set[str]:
    module = importlib.import_module(ENTRYPOINTS_MODULE)
    return set(module._LEGACY_SYMBOL_TARGETS)


def _iter_python_files() -> list[Path]:
    return [path for path in SRC_ROOT.rglob("*.py") if path != ENTRYPOINTS_FILE]


def _entrypoint_aliases(tree: ast.Module) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == ENTRYPOINTS_MODULE:
                    aliases.add(alias.asname or "entrypoints")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "bioetl.composition":
                for alias in node.names:
                    if alias.name == "entrypoints":
                        aliases.add(alias.asname or alias.name)
    return aliases


@pytest.mark.architecture
def test_first_party_src_does_not_import_deprecated_entrypoint_symbols() -> None:
    """Production code must use canonical services/resources APIs directly."""
    legacy_symbols = _legacy_entrypoint_symbols()
    violations: list[str] = []

    for path in _iter_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        entrypoint_aliases = _entrypoint_aliases(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == ENTRYPOINTS_MODULE:
                for alias in node.names:
                    if alias.name in legacy_symbols:
                        rel = path.relative_to(ROOT).as_posix()
                        violations.append(f"{rel}:{node.lineno}: {alias.name}")
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in entrypoint_aliases
                and node.attr in legacy_symbols
            ):
                rel = path.relative_to(ROOT).as_posix()
                violations.append(f"{rel}:{node.lineno}: {node.value.id}.{node.attr}")

    assert not violations, (
        "Deprecated bioetl.composition.entrypoints symbols leaked into first-party "
        "src. Import the canonical services_api/resources_api targets instead:\n"
        + "\n".join(sorted(violations))
    )
