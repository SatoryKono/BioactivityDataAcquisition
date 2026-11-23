"""Keep the typed domain ports facade aligned with its runtime exports."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bioetl.domain import ports


@pytest.mark.architecture
def test_public_ports_have_explicit_stub_reexports_from_runtime_owners() -> None:
    stub = Path(ports.__file__).with_suffix(".pyi")
    tree = ast.parse(stub.read_text(encoding="utf-8"))
    exports = {
        alias.name: node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.asname == alias.name
    }
    assert {name: exports.get(name) for name in ports.__all__} == ports._EXPORT_MODULES
