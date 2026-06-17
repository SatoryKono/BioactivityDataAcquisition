"""Guardrails for explicit runtime registry wiring on composition hot paths."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"

ALLOWED_DEFAULT_REGISTRY_CALLERS = {
    "src/bioetl/composition/factories/pipeline/registry.py",
}

RUNTIME_REGISTRY_SEAMS = {
    "src/bioetl/composition/_services.py": {
        "get_pipeline_runner_service",
        "get_workflow_execution_service",
        "get_workflow_runner_service",
    },
    "src/bioetl/composition/_workflow_services.py": {
        "_default_pipeline_runner_service_factory",
        "get_workflow_execution_service",
        "get_workflow_runner_service",
    },
    "src/bioetl/composition/bootstrap/runtime/runner.py": {
        "bootstrap_pipeline_runner_service",
    },
    "src/bioetl/composition/runtime_builders/runner_builder.py": {
        "build_pipeline_runner",
    },
    "src/bioetl/composition/factories/pipeline/runner.py": {
        "create_runner_factory",
    },
}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _function_param_names(tree: ast.Module) -> dict[str, set[str]]:
    params: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            params[node.name] = {arg.arg for arg in node.args.args}
    return params


def _called_function_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _get_default_registry_call_lines(path: Path) -> list[int]:
    tree = _tree(path)
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _called_function_name(node) == "get_default_registry"
    ]


def test_runtime_registry_hot_path_seams_keep_explicit_registry_parameter() -> None:
    """Runtime builders and service facades must expose registry injection seams."""
    missing: list[str] = []
    for relative_path, function_names in RUNTIME_REGISTRY_SEAMS.items():
        params_by_function = _function_param_names(_tree(ROOT / relative_path))
        for function_name in sorted(function_names):
            params = params_by_function.get(function_name)
            if params is None:
                missing.append(f"{relative_path}:{function_name} missing function")
                continue
            if "registry" not in params:
                missing.append(
                    f"{relative_path}:{function_name} missing registry param"
                )

    assert not missing, (
        "Runtime registry hot paths must keep explicit registry injection seams:\n"
        + "\n".join(missing)
    )


def test_default_registry_singleton_stays_out_of_runtime_hot_paths() -> None:
    """Default registry calls are compatibility-owned, not runtime hot-path wiring."""
    violations: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in ALLOWED_DEFAULT_REGISTRY_CALLERS:
            continue
        for line in _get_default_registry_call_lines(path):
            violations.append(f"{relative_path}:{line}")

    assert not violations, (
        "get_default_registry() leaked outside reviewed compatibility owners:\n"
        + "\n".join(violations)
    )
