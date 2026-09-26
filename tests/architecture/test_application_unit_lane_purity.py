"""Application unit tests must collaborate through ports and test doubles."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_APPLICATION_UNIT_ROOT = _REPO / "tests/unit/application"
_INFRASTRUCTURE_PREFIX = "bioetl.infrastructure"


def _infrastructure_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    # This gate owns module-level collaborators: function-local imports are
    # narrow monkeypatch/type probes and do not wire the test module fixture
    # graph to a concrete adapter.
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(
                alias.name
                for alias in node.names
                if alias.name == _INFRASTRUCTURE_PREFIX
                or alias.name.startswith(f"{_INFRASTRUCTURE_PREFIX}.")
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == _INFRASTRUCTURE_PREFIX or module.startswith(
                f"{_INFRASTRUCTURE_PREFIX}."
            ):
                imports.append(module)
    return imports


def test_application_unit_tests_do_not_wire_concrete_infrastructure() -> None:
    """Keep module-level application fixtures at the ports/fakes boundary."""
    violations = {
        path.relative_to(_REPO).as_posix(): _infrastructure_imports(path)
        for path in sorted(_APPLICATION_UNIT_ROOT.rglob("*.py"))
        if _infrastructure_imports(path)
    }

    assert violations == {}, (
        "Application unit tests must use domain/application ports and test doubles; "
        "move concrete collaboration contracts to integration or repo_backed lanes: "
        f"{violations}"
    )
