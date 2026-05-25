"""Architecture test: no side-effect imports in composition layer.

Verifies that the composition layer does not use side-effect imports
(imports only for their side effects, marked with noqa: F401).

All registrations and initializations should be explicit function calls,
not import-time side effects.
"""

import ast
from pathlib import Path

COMPOSITION_DIR = Path("src/bioetl/composition")


def _find_side_effect_import_violations() -> list[str]:
    violations: list[str] = []
    for py_file in COMPOSITION_DIR.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        violations.extend(_iter_file_side_effect_import_violations(py_file))
    return violations


def _iter_file_side_effect_import_violations(py_file: Path) -> list[str]:
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.split("\n")
    return [
        f"{py_file.name}:{node.lineno}: side-effect import with noqa: F401"
        for node in ast.walk(tree)
        if _is_side_effect_import(node, lines)
    ]


def _is_side_effect_import(node: ast.AST, lines: list[str]) -> bool:
    if not isinstance(node, (ast.Import, ast.ImportFrom)):
        return False
    if node.lineno > len(lines):
        return False
    line = lines[node.lineno - 1]
    return "noqa: F401" in line or "noqa:F401" in line


def _get_bootstrap_pipeline_runner_function() -> ast.FunctionDef:
    bootstrap_file = COMPOSITION_DIR / "bootstrap" / "runtime" / "pipeline.py"
    source = bootstrap_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    bootstrap_func = _find_named_function(tree, "bootstrap_pipeline_runner")
    assert bootstrap_func is not None, "bootstrap_pipeline_runner function not found"
    return bootstrap_func


def _get_prepare_runtime_registry_function() -> ast.FunctionDef:
    phases_file = (
        COMPOSITION_DIR / "bootstrap" / "runtime" / "pipeline_bootstrap_phases.py"
    )
    source = phases_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    prepare_func = _find_named_function(tree, "prepare_runtime_registry")
    assert prepare_func is not None, "prepare_runtime_registry function not found"
    return prepare_func


def _find_named_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _function_calls_name(function_node: ast.FunctionDef, name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
        for node in ast.walk(function_node)
    )


def test_no_side_effect_imports():
    """Composition layer MUST NOT use side-effect imports.

    All registrations and initializations should be explicit function calls,
    not import-time side effects.

    Side-effect imports are identified by the noqa: F401 comment,
    which indicates an unused import kept only for its side effects.
    """
    violations = _find_side_effect_import_violations()

    assert not violations, (
        "Side-effect imports found in composition:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nAll registrations should be explicit function calls."
    )


def test_bootstrap_uses_explicit_registration():
    """bootstrap_pipeline_runner() MUST call register_all_pipelines() explicitly.

    This ensures deterministic initialization without hidden side effects.

    Note: bootstrap_pipeline_runner() is the canonical name (bootstrap_pipeline() is
    a deprecated alias) defined in composition/bootstrap/runtime/pipeline.py
    as part of the CLI/runtime split (see CLAUDE.md §2.1).
    """
    bootstrap_func = _get_bootstrap_pipeline_runner_function()
    prepare_registry_func = _get_prepare_runtime_registry_function()
    calls_register = _function_calls_name(
        bootstrap_func, "register_all_pipelines"
    ) or (
        _function_calls_name(bootstrap_func, "prepare_runtime_registry")
        and _function_calls_name(prepare_registry_func, "register_all_pipelines")
    )

    assert calls_register, (
        "bootstrap_pipeline_runner() must explicitly call register_all_pipelines() "
        "for deterministic initialization"
    )


def test_no_metrics_server_direct_call_in_bootstrap_pipeline():
    """bootstrap_pipeline_runner() MUST NOT call start_metrics_server() directly.

    Metrics server startup should be handled by bootstrap_metrics() or
    bootstrap_observability_bundle() for proper opt-in control.

    Note: bootstrap_pipeline_runner() is the canonical name (bootstrap_pipeline() is
    a deprecated alias) defined in composition/bootstrap/runtime/pipeline.py
    as part of the CLI/runtime split (see CLAUDE.md §2.1).
    """
    bootstrap_func = _get_bootstrap_pipeline_runner_function()
    calls_start_metrics_server = _function_calls_name(
        bootstrap_func, "start_metrics_server"
    )

    assert not calls_start_metrics_server, (
        "bootstrap_pipeline_runner() must not call start_metrics_server() directly. "
        "Use bootstrap_metrics() or bootstrap_observability_bundle() instead."
    )
