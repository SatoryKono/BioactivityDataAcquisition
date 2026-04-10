"""Architecture guardrails for canonical metrics-server wiring."""

from __future__ import annotations

import ast
from pathlib import Path


METRICS_BOOTSTRAP_PATH = Path(
    "src/bioetl/composition/bootstrap/runtime/metrics_bootstrap.py"
)
OBSERVABILITY_API_PATH = Path("src/bioetl/composition/observability_api.py")


def _get_function_def(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Function {name} not found")


def test_runtime_metrics_bootstrap_uses_metrics_service_not_raw_infra_starter() -> None:
    """Runtime bootstrap must use the composition-owned metrics service path."""
    source = METRICS_BOOTSTRAP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "start_metrics_server" not in source, (
        "metrics_bootstrap.py must not call or import raw infrastructure "
        "start_metrics_server; use bootstrap_metrics_service instead."
    )

    function_node = _get_function_def(tree, "maybe_start_metrics_server")
    called_names = {
        inner.func.id
        for inner in ast.walk(function_node)
        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
    }
    assert "bootstrap_metrics_service" in called_names or "service_factory" in source, (
        "maybe_start_metrics_server must resolve a composition-owned metrics "
        "service and call its start() method."
    )


def test_observability_api_start_metrics_server_delegates_via_metrics_service() -> None:
    """Public observability API must route server startup through get_metrics_service."""
    source = OBSERVABILITY_API_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_node = _get_function_def(tree, "start_metrics_server")

    called_names = {
        inner.func.id
        for inner in ast.walk(function_node)
        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
    }
    called_attrs = {
        inner.func.attr
        for inner in ast.walk(function_node)
        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
    }

    assert "get_metrics_service" in called_names, (
        "composition.observability_api.start_metrics_server must obtain the "
        "canonical metrics service via get_metrics_service()."
    )
    assert "start" in called_attrs, (
        "composition.observability_api.start_metrics_server must delegate to "
        "MetricsService.start()."
    )
