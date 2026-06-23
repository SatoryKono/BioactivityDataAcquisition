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


def _fixture_keyword_metadata(keyword: ast.keyword) -> tuple[str | None, bool | None]:
    if not isinstance(keyword.value, ast.Constant):
        return None, None
    if keyword.arg == "scope" and isinstance(keyword.value.value, str):
        return keyword.value.value, None
    if keyword.arg == "autouse":
        return None, bool(keyword.value.value)
    return None, None


def _fixture_call_metadata(decorator: ast.Call) -> tuple[str | None, bool]:
    scope: str | None = None
    autouse = False
    for keyword in decorator.keywords:
        keyword_scope, keyword_autouse = _fixture_keyword_metadata(keyword)
        if keyword_scope is not None:
            scope = keyword_scope
        if keyword_autouse is not None:
            autouse = keyword_autouse
    return scope, autouse


def _fixture_decorator_metadata(
    decorator: ast.expr,
    *,
    current_scope: str | None,
    current_autouse: bool,
) -> tuple[bool, str | None, bool]:
    if not _is_fixture_target(decorator):
        return False, current_scope, current_autouse
    if not isinstance(decorator, ast.Call):
        return True, current_scope, current_autouse
    scope, autouse = _fixture_call_metadata(decorator)
    return True, scope, autouse


def _fixture_metadata(
    function: ast.FunctionDef,
) -> tuple[bool, str | None, bool]:
    scope: str | None = None
    autouse = False
    is_fixture = False
    for decorator in function.decorator_list:
        matched, scope, autouse = _fixture_decorator_metadata(
            decorator,
            current_scope=scope,
            current_autouse=autouse,
        )
        is_fixture = is_fixture or matched
    return is_fixture, scope, autouse


def _env_var_refs(node: ast.AST) -> set[str]:
    refs: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if child.value in TARGET_ENV_VARS:
                refs.add(child.value)
    return refs


@pytest.mark.architecture
def test_dq_fixture_policy__global_mutation__14c6d573() -> None:
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
def test_dq_fixture_policy__named_fixtures__d3fbe63c() -> None:
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
