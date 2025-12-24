"""Architecture test: no side-effect imports in composition layer.

Verifies that the composition layer does not use side-effect imports
(imports only for their side effects, marked with noqa: F401).

All registrations and initializations should be explicit function calls,
not import-time side effects.
"""

import ast
from pathlib import Path


COMPOSITION_DIR = Path("src/bioetl/composition")


def test_no_side_effect_imports():
    """Composition layer MUST NOT use side-effect imports.

    All registrations and initializations should be explicit function calls,
    not import-time side effects.

    Side-effect imports are identified by the noqa: F401 comment,
    which indicates an unused import kept only for its side effects.
    """
    violations = []

    for py_file in COMPOSITION_DIR.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        source = py_file.read_text()
        tree = ast.parse(source)
        lines = source.split("\n")

        for node in ast.walk(tree):
            # Check for noqa: F401 comments (indicates unused import = side-effect)
            if isinstance(node, ast.Import | ast.ImportFrom):
                if node.lineno <= len(lines):
                    line = lines[node.lineno - 1]
                    if "noqa: F401" in line or "noqa:F401" in line:
                        violations.append(
                            f"{py_file.name}:{node.lineno}: side-effect import with noqa: F401"
                        )

    assert not violations, (
        "Side-effect imports found in composition:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nAll registrations should be explicit function calls."
    )


def test_bootstrap_uses_explicit_registration():
    """bootstrap_pipeline() MUST call register_all_pipelines() explicitly.

    This ensures deterministic initialization without hidden side effects.
    """
    bootstrap_file = COMPOSITION_DIR / "bootstrap.py"
    source = bootstrap_file.read_text()
    tree = ast.parse(source)

    # Find bootstrap_pipeline function
    bootstrap_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "bootstrap_pipeline":
            bootstrap_func = node
            break

    assert bootstrap_func is not None, "bootstrap_pipeline function not found"

    # Check that register_all_pipelines() is called in the function body
    calls_register = False
    for node in ast.walk(bootstrap_func):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "register_all_pipelines":
                calls_register = True
                break

    assert calls_register, (
        "bootstrap_pipeline() must explicitly call register_all_pipelines() "
        "for deterministic initialization"
    )


def test_no_metrics_server_direct_call_in_bootstrap_pipeline():
    """bootstrap_pipeline() MUST NOT call start_metrics_server() directly.

    Metrics server startup should be handled by bootstrap_metrics() or
    bootstrap_observability() for proper opt-in control.
    """
    bootstrap_file = COMPOSITION_DIR / "bootstrap.py"
    source = bootstrap_file.read_text()
    tree = ast.parse(source)

    # Find bootstrap_pipeline function
    bootstrap_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "bootstrap_pipeline":
            bootstrap_func = node
            break

    assert bootstrap_func is not None, "bootstrap_pipeline function not found"

    # Check that start_metrics_server() is NOT called directly
    for node in ast.walk(bootstrap_func):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "start_metrics_server":
                raise AssertionError(
                    "bootstrap_pipeline() must not call start_metrics_server() directly. "
                    "Use bootstrap_metrics() or bootstrap_observability() instead."
                )
