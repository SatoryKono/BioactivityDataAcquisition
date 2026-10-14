"""CF-030 routing checker: every in-tree ``vcr_config`` fixture must build on
``build_base_vcr_config`` (directly or via the rebalance helper), so the
canonical secret filter set cannot be bypassed by a hand-rolled config dict."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).resolve().parents[2]

_BASE_HELPER = ("tests.helpers.vcr_config", "build_base_vcr_config")
_REBALANCE_HELPER = (
    "tests.integration.adapters.vcr_rebalance_support",
    "build_vcr_config",
)

pytestmark = pytest.mark.unit


def _routes_through_helper(
    tree: ast.Module,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    allowed_imports: tuple[tuple[str, str], ...],
) -> bool:
    """Require the fixture to return an imported, approved helper directly."""
    approved_names = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if (node.module, alias.name) in allowed_imports
    }
    nodes = list(ast.walk(function))
    if any(
        (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Store)
            and node.id in approved_names
        )
        or (isinstance(node, ast.arg) and node.arg in approved_names)
        or (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node is not function
        )
        for node in nodes
    ):
        return False
    results = [node.value for node in nodes if isinstance(node, ast.Return)]
    return bool(results) and all(
        isinstance(result, ast.Call)
        and isinstance(result.func, ast.Name)
        and result.func.id in approved_names
        for result in results
    )


def test_every_in_tree_vcr_config_fixture_routes_through_base_helper() -> None:
    """Fail when any tests/** vcr_config fixture bypasses the canonical helper."""
    offenders: list[str] = []
    for path in sorted(_TESTS_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "vcr_config" not in text:
            continue
        tree = ast.parse(text)
        for function in ast.walk(tree):
            if (
                isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                and function.name == "vcr_config"
                and not _routes_through_helper(
                    tree, function, (_BASE_HELPER, _REBALANCE_HELPER)
                )
            ):
                offenders.append(path.relative_to(_TESTS_ROOT).as_posix())

    assert offenders == []


def test_rebalance_wrapper_returns_canonical_base_helper() -> None:
    """Require the rebalance wrapper to return the approved VCR configuration."""
    path = _TESTS_ROOT / "integration/adapters/vcr_rebalance_support.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_vcr_config"
    )
    assert _routes_through_helper(tree, function, (_BASE_HELPER,))


@pytest.mark.parametrize(
    "body",
    [
        'return {"record_mode": "all"}',
        '# build_base_vcr_config\n    return {"record_mode": "all"}',
        'build_base_vcr_config()\n    return {"record_mode": "all"}',
        "if True:\n        return {}\n    return build_base_vcr_config()",
        "def nested():\n        return build_base_vcr_config()\n    return {}",
        "build_base_vcr_config = lambda: {}\n    return build_base_vcr_config()",
    ],
)
def test_routing_rejects_unused_or_discarded_helper(body: str) -> None:
    """Reject fixtures that call or mention the helper but bypass its result."""
    source = (
        "from tests.helpers.vcr_config import build_base_vcr_config\n"
        f"def vcr_config():\n    {body}\n"
    )
    tree = ast.parse(source)
    function = tree.body[1]
    assert isinstance(function, ast.FunctionDef)
    assert not _routes_through_helper(tree, function, (_BASE_HELPER,))


def test_routing_accepts_canonical_import_alias() -> None:
    """Accept an alias imported from the canonical helper module."""
    tree = ast.parse(
        "from tests.helpers.vcr_config import build_base_vcr_config as base\n"
        "def vcr_config():\n    return base()\n"
    )
    function = tree.body[1]
    assert isinstance(function, ast.FunctionDef)
    assert _routes_through_helper(tree, function, (_BASE_HELPER,))


def test_routing_rejects_unapproved_helper_origin() -> None:
    """Reject a matching helper name imported from an unapproved module."""
    tree = ast.parse(
        "from elsewhere import build_base_vcr_config\n"
        "def vcr_config():\n    return build_base_vcr_config()\n"
    )
    function = tree.body[1]
    assert isinstance(function, ast.FunctionDef)
    assert not _routes_through_helper(tree, function, (_BASE_HELPER,))
