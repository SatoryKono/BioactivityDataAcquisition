# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guardrail for explicit postrun DI."""

from __future__ import annotations

import pytest

import ast
from pathlib import Path


pytestmark = pytest.mark.architecture

POSTRUN_SERVICE_PATH = Path("src/bioetl/application/core/postrun/service.py")
POSTRUN_COLLABORATORS_PATH = Path(
    "src/bioetl/application/core/postrun/_service_collaborators.py"
)


def _iter_called_names(function_node: ast.FunctionDef) -> set[str]:
    """Return simple constructor/function names called inside a function."""
    names: set[str] = set()
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def test_postrun_service_does_not_construct_noop_tracer() -> None:
    """PostrunService must consume an explicit tracer from composition/tests."""
    content = POSTRUN_SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            assert "NoOpTracing" not in _iter_called_names(node), (
                "PostrunService.__init__ must not construct NoOpTracing; "
                "build tracing defaults in composition or test support."
            )
            return

    raise AssertionError("PostrunService.__init__ not found")


def test_postrun_collaborator_resolution_does_not_construct_noop_metrics() -> None:
    """Postrun collaborator resolution must consume explicit metrics wiring."""
    content = POSTRUN_COLLABORATORS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "resolve_postrun_collaborators"
        ):
            assert "NoOpMetrics" not in _iter_called_names(node), (
                "resolve_postrun_collaborators must not construct NoOpMetrics; "
                "build metrics defaults in composition or test support."
            )
            return

    raise AssertionError("resolve_postrun_collaborators not found")
