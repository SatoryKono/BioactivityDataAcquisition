"""Ratchet and unit coverage for AUD-002 AST probe extract (#10526)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import _core_ast as ast_probes

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
AST_MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core_ast.py"
# Line count on origin/main after the HTTP slice (#10638).
_CORE_LOC_BEFORE_AST_SLICE = 17402


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_ast_probes_own_parse_helpers_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    ast_text = AST_MOD.read_text(encoding="utf-8")
    assert "def _parse_python_ast" not in core_text
    assert "def _parse_python_ast" in ast_text
    assert "def _signature_hash" in ast_text
    ast_loc = _loc(AST_MOD)
    core_loc = _loc(CORE)
    assert core_loc < _CORE_LOC_BEFORE_AST_SLICE
    assert ast_loc < 500
    assert _core._parse_python_ast is ast_probes._parse_python_ast


def test_parse_python_ast_rejects_non_python_and_syntax_errors(tmp_path: Path) -> None:
    txt = tmp_path / "notes.md"
    txt.write_text("# not python\n", encoding="utf-8")
    assert ast_probes._parse_python_ast(txt) is None
    broken = tmp_path / "broken.py"
    broken.write_text("def oops(\n", encoding="utf-8")
    assert ast_probes._parse_python_ast(broken) is None


def test_protocol_and_import_probes(tmp_path: Path) -> None:
    module = tmp_path / "ports.py"
    module.write_text(
        "from typing import Protocol\n"
        "from bioetl.domain.ports.storage import SilverWriter as Writer\n"
        "\n"
        "class RowPort(Protocol):\n"
        "    def read(self) -> None: ...\n"
        "\n"
        "class ActivitySchema:\n"
        "    activity_id: str\n",
        encoding="utf-8",
    )
    assert ast_probes._protocol_class_names(module) == ["RowPort"]
    assert ast_probes._dataframe_model_class_names(module) == ["ActivitySchema"]
    assert ast_probes._imported_symbols(module) == [
        ("typing", "Protocol", "Protocol"),
        ("bioetl.domain.ports.storage", "SilverWriter", "Writer"),
    ]
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        imported.update(
            ast_probes._matching_imported_module_names(node, ("bioetl.domain.ports",))
        )
    assert "bioetl.domain.ports.storage" in imported


def test_callable_metrics_count_branches_and_helper_calls() -> None:
    tree = ast.parse(
        "def sample(flag: bool) -> int:\n"
        "    if flag:\n"
        "        return _helper_codec(1)\n"
        "    return 0\n"
    )
    func = tree.body[0]
    assert isinstance(func, ast.FunctionDef)
    assert ast_probes._callable_branch_count(func) >= 1
    assert ast_probes._callable_helper_call_count(func) == 1
    assert ast_probes._callable_call_count(func) == 1
    call = next(node for node in ast.walk(func) if isinstance(node, ast.Call))
    assert ast_probes._base_name(call.func) == "_helper_codec"
    digest = ast_probes._signature_hash(func)
    assert len(digest) == 64
    assert ast_probes._normalized_callable_hash(func) != digest
