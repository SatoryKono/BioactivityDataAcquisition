from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path("src/bioetl")


def _py_files() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if "tests" not in p.parts]


def test_no_sentinel_values() -> None:
    pattern = re.compile(r"=\s*-1|\"N/A\"|\"n/a\"|=\s*9999")
    bad: list[str] = []
    for p in _py_files():
        txt = p.read_text(encoding="utf-8")
        if pattern.search(txt):
            bad.append(str(p))
    assert not bad, f"Sentinel values found: {bad}"


def test_no_hardcoded_secrets() -> None:
    pattern = re.compile(
        r"password\s*=\s*[\"']|api_key\s*=\s*[\"']|secret\s*=\s*[\"']",
        re.I,
    )
    bad: list[str] = []
    for p in _py_files():
        if "ports" in p.parts or "protocol" in p.name:
            continue
        txt = p.read_text(encoding="utf-8")
        if pattern.search(txt):
            bad.append(str(p))
    assert not bad, f"Hardcoded secrets found: {bad}"


def test_no_print_in_production() -> None:
    pattern = re.compile(r"^\s*print\(", re.M)
    bad: list[str] = []
    for p in _py_files():
        if Path("src/bioetl/interfaces/cli") in p.parents:
            continue
        txt = p.read_text(encoding="utf-8")
        if pattern.search(txt):
            bad.append(str(p))
    assert not bad, f"print() found: {bad}"


def test_no_blocking_io_in_async() -> None:
    bad: list[str] = []
    for p in _py_files():
        source = p.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                body = ast.get_source_segment(source, node) or ""
                if "open(" in body or "requests." in body or "urllib" in body:
                    bad.append(f"{p}:{node.name}")
    assert not bad, f"Blocking IO in async def: {bad}"
