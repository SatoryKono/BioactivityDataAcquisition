"""Architecture guardrail for explicit transformer DI."""

from __future__ import annotations

import ast
from pathlib import Path


BASE_TRANSFORMER_PATH = Path("src/bioetl/application/core/base_transformer/base.py")
FORBIDDEN_CONSTRUCTORS = {
    "NoOpTracing",
    "NoOpMetrics",
    "IdentityService",
    "NoOpPiiHasher",
    "DataNormalizationService",
    "_DefaultContractPolicy",
}


def _iter_constructor_calls(function_node: ast.FunctionDef) -> list[str]:
    """Return constructor names called inside the target function."""
    names: list[str] = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.append(func.id)
        elif isinstance(func, ast.Attribute):
            names.append(func.attr)
    return names


def test_base_transformer_init_does_not_construct_default_collaborators() -> None:
    """BaseTransformer must consume injected collaborators, not create them."""
    content = BASE_TRANSFORMER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "BaseTransformer":
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                calls = set(_iter_constructor_calls(item))
                forbidden = sorted(FORBIDDEN_CONSTRUCTORS & calls)
                assert not forbidden, (
                    "BaseTransformer.__init__ must not create concrete defaults; "
                    f"found: {', '.join(forbidden)}"
                )
                return

    raise AssertionError("BaseTransformer.__init__ not found")
