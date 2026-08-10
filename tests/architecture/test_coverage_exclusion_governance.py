"""Guard narrowly scoped source coverage exclusions."""

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


def test_composite_protocol_coverage_exclusions_remain_declaration_only() -> None:
    """Excluded Protocol suites must never acquire executable behavior."""
    source = _COMPOSITE_PROTOCOLS.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    classes = [
        node for node in ast.parse(source).body if isinstance(node, ast.ClassDef)
    ]

    assert len(classes) == 15
    for class_node in classes:
        assert any(
            isinstance(base, ast.Name) and base.id == "Protocol"
            for base in class_node.bases
        )
        header_lines = source_lines[class_node.lineno - 1 : class_node.body[0].lineno]
        assert any(_DECLARATION_MARKER in line for line in header_lines)
        assert class_node.body

        for member in class_node.body:
            assert isinstance(member, ast.FunctionDef)
            assert [
                decorator.id
                for decorator in member.decorator_list
                if isinstance(decorator, ast.Name)
            ] == ["property"]
            assert len(member.body) == 1
            expression = member.body[0]
            assert isinstance(expression, ast.Expr)
            assert isinstance(expression.value, ast.Constant)
            assert expression.value.value is Ellipsis
