# pyright: reportArgumentType=false
"""CLI production registry path must prefer explicit registries (#7606 / #7605)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLI_ROOT = ROOT / "src" / "bioetl" / "interfaces" / "cli"
FORBIDDEN = "get_default_registry"


def _calls_get_default_registry(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == FORBIDDEN:
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    return hits


@pytest.mark.architecture
def test_cli_tree_does_not_call_get_default_registry() -> None:
    """Production CLI must not call shared default registry as primary path."""
    violations: list[str] = []
    for path in CLI_ROOT.rglob("*.py"):
        violations.extend(_calls_get_default_registry(path))
    assert not violations, (
        "CLI production path must use build_cli_registry()/explicit PipelineRegistry; "
        f"found get_default_registry() calls:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_cli_registry_helpers_document_explicit_registry() -> None:
    text = (CLI_ROOT / "registry_helpers.py").read_text(encoding="utf-8")
    assert "build_cli_registry" in text
    assert "create_registry" in text or "PipelineRegistry" in text
