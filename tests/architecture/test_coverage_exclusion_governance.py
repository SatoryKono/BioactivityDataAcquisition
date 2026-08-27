"""Guard declaration-only contracts without hiding branch debt."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_COMPOSITE_PROTOCOLS = (
    _REPO / "src/bioetl/domain/composite/config_composite_protocols.py"
)
_DECLARATION_MARKER = "pragma: no cover - declaration-only contract"


def test_composite_protocols_remain_declaration_only_and_measured() -> None:
    """Protocol suites must stay declarative and must not carry broad exclusions."""
    source = _COMPOSITE_PROTOCOLS.read_text(encoding="utf-8")
    classes = [
        node for node in ast.parse(source).body if isinstance(node, ast.ClassDef)
    ]

    assert _DECLARATION_MARKER not in source
    assert len(classes) == 15
    for class_node in classes:
        assert any(
            isinstance(base, ast.Name) and base.id == "Protocol"
            for base in class_node.bases
        )
        assert class_node.body

        for member in class_node.body:
            assert isinstance(member, ast.FunctionDef)
            assert [
                decorator.id
                for decorator in member.decorator_list
                if isinstance(decorator, ast.Name)
            ] == ["property"]
            assert 1 <= len(member.body) <= 2
            if len(member.body) == 2:
                docstring = member.body[0]
                assert isinstance(docstring, ast.Expr)
                assert isinstance(docstring.value, ast.Constant)
                assert isinstance(docstring.value.value, str)
            expression = member.body[-1]
            assert isinstance(expression, ast.Expr)
            assert isinstance(expression.value, ast.Constant)
            assert expression.value.value is Ellipsis
