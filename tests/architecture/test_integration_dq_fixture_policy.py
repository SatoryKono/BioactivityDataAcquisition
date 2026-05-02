"""Architecture guard for integration DQ fixture policy."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_CONFTEST = ROOT / "tests" / "integration" / "conftest.py"
TARGET_ENV_VARS = {
    "BIOETL_TEST_RELAXED_DQ",
    "BIOETL_PIPELINE__RELAXED_DQ",
}


def _read_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _is_fixture_target(node: ast.expr) -> bool:
    func: ast.expr
    if isinstance(node, ast.Call):
        func = node.func
    else:
        func = node
    if isinstance(func, ast.Attribute):
        return func.attr == "fixture"
    if isinstance(func, ast.Name):
        return func.id == "fixture"
    return False


def _fixture_metadata(
    function: ast.FunctionDef,
) -> tuple[bool, str | None, bool]:
    scope: str | None = None
    autouse = False
    is_fixture = False
    for decorator in function.decorator_list:
        if not _is_fixture_target(decorator):
            continue
        is_fixture = True
        if not isinstance(decorator, ast.Call):
            continue
        for keyword in decorator.keywords:
            if keyword.arg == "scope" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    scope = keyword.value.value
            if keyword.arg == "autouse" and isinstance(keyword.value, ast.Constant):
                autouse = bool(keyword.value.value)
    return is_fixture, scope, autouse


def _env_var_refs(node: ast.AST) -> set[str]:
    refs: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if child.value in TARGET_ENV_VARS:
                refs.add(child.value)
    return refs


@pytest.mark.architecture
def test_relaxed_dq_env_is_not_session_autouse_global_mutation() -> None:
    tree = _read_tree(INTEGRATION_CONFTEST)
    violating_fixtures: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        is_fixture, scope, autouse = _fixture_metadata(node)
        if not is_fixture:
            continue
        if scope == "session" and autouse and _env_var_refs(node):
            violating_fixtures.append(node.name)

    assert not violating_fixtures, (
        "Integration conftest must not use session-scoped autouse fixtures to "
        "mutate relaxed DQ environment variables."
    )


@pytest.mark.architecture
def test_relaxed_dq_mode_is_exposed_only_via_explicit_named_fixtures() -> None:
    tree = _read_tree(INTEGRATION_CONFTEST)

    fixtures: dict[str, tuple[str | None, bool, set[str]]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        is_fixture, scope, autouse = _fixture_metadata(node)
        if not is_fixture:
            continue
        fixtures[node.name] = (scope, autouse, _env_var_refs(node))

    assert "relaxed_dq_env" in fixtures
    assert "strict_dq_env" in fixtures

    relaxed_scope, relaxed_autouse, relaxed_refs = fixtures["relaxed_dq_env"]
    strict_scope, strict_autouse, strict_refs = fixtures["strict_dq_env"]

    assert relaxed_scope != "session"
    assert strict_scope != "session"
    assert relaxed_autouse is False
    assert strict_autouse is False
    assert TARGET_ENV_VARS <= relaxed_refs
    assert TARGET_ENV_VARS <= strict_refs

    extras = [
        fixture_name
        for fixture_name, (_scope, _autouse, refs) in fixtures.items()
        if refs and fixture_name not in {"relaxed_dq_env", "strict_dq_env"}
    ]
    assert not extras, (
        "Relaxed DQ env vars must be controlled only by explicit fixtures: "
        f"{sorted(extras)}"
    )
