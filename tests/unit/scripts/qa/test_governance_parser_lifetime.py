"""Governance rescans must release parsed modules and observe current source."""

from __future__ import annotations

import ast
import gc
import weakref
from pathlib import Path

import pytest

from scripts.engineering.qa import report_test_governance_audit as audit

pytestmark = pytest.mark.unit


def test_parser_releases_tree_and_rereads_changed_source(monkeypatch) -> None:
    source = "def test_first():\n    assert True\n"
    monkeypatch.setattr(audit, "_read_text_file", lambda path: source)
    path = Path("test_dynamic.py")
    tree, error = audit._parse_test_module_source(path, relative=path.name)
    assert error is None
    assert isinstance(tree, ast.Module)
    assert tree.body[0].name == "test_first"
    reference = weakref.ref(tree)
    del tree
    gc.collect()
    assert reference() is None

    source = "def test_second():\n    assert False\n"
    changed_tree, error = audit._parse_test_module_source(path, relative=path.name)
    assert error is None
    assert isinstance(changed_tree, ast.Module)
    assert changed_tree.body[0].name == "test_second"


def test_parser_keeps_syntax_error_diagnostics(monkeypatch) -> None:
    monkeypatch.setattr(audit, "_read_text_file", lambda path: "def broken(")
    tree, error = audit._parse_test_module_source(
        Path("broken.py"), relative="broken.py"
    )
    assert tree is None
    assert error is not None
    assert error["path"] == "broken.py"
    assert "never closed" in error["error"]
