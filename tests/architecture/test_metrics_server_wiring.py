"""Architecture guardrails for canonical metrics-server wiring."""

from __future__ import annotations

import ast
from pathlib import Path


METRICS_BOOTSTRAP_PATH = Path(
    "src/bioetl/composition/bootstrap/runtime/metrics_bootstrap.py"
)
OBSERVABILITY_API_PATH = Path("src/bioetl/composition/observability_api.py")
RUNTIME_OBSERVABILITY_PATH = Path(
    "src/bioetl/composition/bootstrap/runtime/observability.py"
)
RUNTIME_INIT_PATH = Path("src/bioetl/composition/bootstrap/runtime/__init__.py")
PIPELINE_EXECUTION_PATH = Path("src/bioetl/composition/_pipeline_execution.py")
OBSERVABILITY_RESOLUTION_PATH = Path(
    "src/bioetl/composition/observability_resolution.py"
)
RUNTIME_OBSERVABILITY_BUILDER_PATH = Path(
    "src/bioetl/composition/runtime_builders/observability_builder.py"
)


def _get_function_def(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Function {name} not found")


def _collect_called_names_and_attrs(
    function_node: ast.FunctionDef,
) -> tuple[set[str], set[str]]:
    """Collect direct call names and attribute names from a function body."""
    called_names: set[str] = set()
    called_attrs: set[str] = set()
    for inner in ast.walk(function_node):
        if not isinstance(inner, ast.Call):
            continue
        func = inner.func
        if isinstance(func, ast.Name):
            called_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            called_attrs.add(func.attr)
    return called_names, called_attrs


def _collect_forbidden_metrics_server_usage(
    tree: ast.AST,
) -> tuple[set[str], set[str]]:
    """Collect forbidden raw metrics-server imports and callsites."""
    forbidden_imports: set[str] = set()
    forbidden_calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "start_metrics_server":
                    forbidden_imports.add(alias.name)
            continue
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "start_metrics_server":
            forbidden_calls.add(func.id)
        elif isinstance(func, ast.Attribute) and func.attr == "start_metrics_server":
            forbidden_calls.add(func.attr)
    return forbidden_imports, forbidden_calls


def _collect_exported_and_imported_names(path: Path) -> tuple[set[str], set[str]]:
    """Collect imported names and explicitly exported names for a module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    exported_names: set[str] = set()
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported_names.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not (
                isinstance(target, ast.Name)
                and target.id in {"__all__", "_PUBLIC_EXPORTS"}
            ):
                continue
            value = node.value
            if isinstance(value, ast.List):
                exported_names.update(
                    elt.value
                    for elt in value.elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                )
            elif isinstance(value, ast.Dict):
                exported_names.update(
                    key.value
                    for key in value.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                )
    return imported_names, exported_names


def test_runtime_metrics_bootstrap_uses_metrics_service_not_raw_infra_starter() -> None:
    """Runtime bootstrap must use the composition-owned metrics service path."""
    source = METRICS_BOOTSTRAP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports, forbidden_calls = _collect_forbidden_metrics_server_usage(tree)

    assert not forbidden_imports and not forbidden_calls, (
        "metrics_bootstrap.py must not call or import raw infrastructure "
        "start_metrics_server; use create_metrics_service instead."
    )

    function_node = _get_function_def(tree, "maybe_start_metrics_server")
    called_names, _ = _collect_called_names_and_attrs(function_node)
    assert "create_metrics_service" in called_names or "service_factory" in source, (
        "maybe_start_metrics_server must resolve a composition-owned metrics "
        "service and call its start() method."
    )


def test_observability_api_start_metrics_server_delegates_via_metrics_service() -> None:
    """Public observability API must route server startup through get_metrics_service."""
    source = OBSERVABILITY_API_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_node = _get_function_def(tree, "start_metrics_server")

    called_names, called_attrs = _collect_called_names_and_attrs(function_node)

    assert "get_metrics_service" in called_names, (
        "composition.observability_api.start_metrics_server must obtain the "
        "canonical metrics service via get_metrics_service()."
    )
    assert "start" in called_attrs, (
        "composition.observability_api.start_metrics_server must delegate to "
        "MetricsService.start()."
    )


def test_observability_api_push_metrics_delegates_via_metrics_service() -> None:
    """Public observability API must route Pushgateway publication through MetricsService."""
    source = OBSERVABILITY_API_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_node = _get_function_def(tree, "push_metrics_to_gateway")

    called_names, called_attrs = _collect_called_names_and_attrs(function_node)

    assert "get_metrics_service" in called_names, (
        "composition.observability_api.push_metrics_to_gateway must obtain the "
        "canonical metrics service via get_metrics_service()."
    )
    assert "push_to_gateway" in called_attrs, (
        "composition.observability_api.push_metrics_to_gateway must delegate to "
        "MetricsService.push_to_gateway()."
    )
    assert "infrastructure.observability.server" not in source, (
        "composition.observability_api.push_metrics_to_gateway must not import "
        "Pushgateway helpers from infrastructure directly."
    )


def test_runtime_observability_modules_do_not_reexport_raw_start_metrics_server() -> (
    None
):
    """Legacy raw start_metrics_server exports must stay out of runtime bootstrap surface."""
    for path in (RUNTIME_OBSERVABILITY_PATH, RUNTIME_INIT_PATH):
        imported_names, exported_names = _collect_exported_and_imported_names(path)

        assert "start_metrics_server" not in imported_names | exported_names, (
            f"{path} must not import or re-export raw start_metrics_server; "
            "use composition.observability_api.start_metrics_server instead."
        )


def test_pipeline_execution_uses_composition_pushgateway_seam() -> None:
    """Pipeline execution must not import Pushgateway helpers from infrastructure directly."""
    source = PIPELINE_EXECUTION_PATH.read_text(encoding="utf-8")
    assert "infrastructure.observability.server" not in source, (
        "_pipeline_execution.py must use composition-owned push_metrics_to_gateway "
        "instead of importing infrastructure Pushgateway helpers directly."
    )


def test_runtime_observability_builder_delegates_noop_resolution_to_canonical_helper() -> (
    None
):
    """Compatibility builder must not reintroduce ad-hoc NoOp observability imports."""
    source = RUNTIME_OBSERVABILITY_BUILDER_PATH.read_text(encoding="utf-8")
    assert "from bioetl.domain.ports.noop" not in source, (
        "runtime_builders/observability_builder.py must not import NoOp ports "
        "directly; use composition.observability_resolution instead."
    )
    assert "composition.observability_resolution" in source, (
        "runtime_builders/observability_builder.py must delegate fallback "
        "resolution to composition.observability_resolution."
    )


def test_canonical_observability_resolution_owns_noop_port_imports() -> None:
    """Composition-owned fallback helper remains the single shared NoOp resolution seam."""
    source = OBSERVABILITY_RESOLUTION_PATH.read_text(encoding="utf-8")
    assert "from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing" in source, (
        "observability_resolution.py should remain the composition-owned seam "
        "for shared NoOp metrics/tracing resolution."
    )
