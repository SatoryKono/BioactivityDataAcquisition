"""Guardrails for the removed checkpoint compatibility V2 surface."""

from __future__ import annotations

import ast
from importlib import import_module
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_NAME = "bioetl.application.services.checkpoint_compatibility_service_v2"
MODULE_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "checkpoint_compatibility_service_v2.py"
)


@pytest.mark.architecture
def test_checkpoint_compatibility_v2_module_has_been_removed() -> None:
    """The legacy V2 checkpoint compatibility module must stay absent."""
    assert not MODULE_PATH.exists()


@pytest.mark.architecture
def test_checkpoint_compatibility_v2_import_fails() -> None:
    """Removed V2 compatibility surface must remain unimportable."""
    with pytest.raises(ModuleNotFoundError):
        import_module(MODULE_NAME)


def _find_importers(root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name for alias in node.names}
                if MODULE_NAME in names:
                    violations.append(path.relative_to(ROOT).as_posix())
                    break
            if isinstance(node, ast.ImportFrom):
                if node.module == MODULE_NAME:
                    violations.append(path.relative_to(ROOT).as_posix())
                    break
    return violations


@pytest.mark.architecture
def test_checkpoint_compatibility_v2_not_imported_from_src() -> None:
    """First-party runtime code must use the canonical checkpoint path only."""
    violations = _find_importers(ROOT / "src")
    assert not violations


@pytest.mark.architecture
def test_checkpoint_compatibility_v2_not_imported_from_tests() -> None:
    """Tests must not preserve the removed V2 public surface."""
    violations = _find_importers(ROOT / "tests")
    assert not violations
