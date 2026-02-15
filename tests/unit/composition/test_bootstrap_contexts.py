"""Tests for composition bootstrap context declarations."""

from __future__ import annotations

import ast
from pathlib import Path


def _get_bootstrap_contexts_ast() -> ast.Module:
    source = Path("src/bioetl/composition/bootstrap_contexts.py").read_text(
        encoding="utf-8"
    )
    return ast.parse(source)


class TestRateLimitContextNaming:
    """Regression tests for composition rate limit context naming."""

    def test_rate_limit_context_class_declared(self) -> None:
        """RateLimitContext class is declared in bootstrap_contexts."""
        module_ast = _get_bootstrap_contexts_ast()
        class_names = {
            node.name for node in module_ast.body if isinstance(node, ast.ClassDef)
        }

        assert "RateLimitContext" in class_names

    def test_legacy_rate_limit_config_not_declared(self) -> None:
        """Legacy RateLimitConfig class name is no longer declared."""
        module_ast = _get_bootstrap_contexts_ast()
        class_names = {
            node.name for node in module_ast.body if isinstance(node, ast.ClassDef)
        }

        assert "RateLimitConfig" not in class_names
