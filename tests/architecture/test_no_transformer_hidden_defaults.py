"""Architecture guardrails for explicit transformer DI."""

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


def _load_base_transformer_init() -> ast.FunctionDef:
    content = BASE_TRANSFORMER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(content)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "BaseTransformer":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    return item
    raise AssertionError("BaseTransformer.__init__ not found")


def test_base_transformer_init_does_not_construct_hidden_defaults() -> None:
    """BaseTransformer must resolve collaborators, not construct them inline."""
    init_fn = _load_base_transformer_init()
    forbidden_calls: list[str] = []

    for node in ast.walk(init_fn):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CONSTRUCTORS:
                forbidden_calls.append(func.id)

    assert not forbidden_calls, (
        "BaseTransformer.__init__ must not construct concrete collaborators inline. "
        f"Found: {sorted(set(forbidden_calls))}"
    )
