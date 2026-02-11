from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path("src/bioetl")


def _py_files() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if "tests" not in p.parts]


def test_no_sentinel_values() -> None:
    patterns = [r"\=\s*\-1\b", r'"N/A"', r'"n/a"', r"\=\s*9999\b"]
    rx = re.compile("|".join(patterns))
    violations: list[str] = []
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if rx.search(line):
                violations.append(f"{path}:{i}: {line.strip()}")
    assert not violations, "Sentinel values found:\n" + "\n".join(violations[:50])


def test_no_hardcoded_secrets() -> None:
    rx = re.compile(r"(password|api_key|secret)\s*=\s*['\"][^'\"]+['\"]", re.I)
    violations: list[str] = []
    for path in _py_files():
        if "ports" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                violations.append(f"{path}:{i}: {line.strip()}")
    assert not violations, "Hardcoded secrets found:\n" + "\n".join(violations[:50])


def test_no_print_in_production() -> None:
    violations: list[str] = []
    for path in _py_files():
        if path.match("src/bioetl/interfaces/cli/*") or "interfaces/cli" in str(path):
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.match(r"^\s*print\(", line):
                violations.append(f"{path}:{i}: {line.strip()}")
    assert not violations, "print() usage found:\n" + "\n".join(violations[:50])


def test_no_blocking_io_in_async() -> None:
    violations: list[str] = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                segment = (
                    ast.get_source_segment(path.read_text(encoding="utf-8"), node) or ""
                )
                if any(x in segment for x in ["open(", "requests.", "urllib"]):
                    violations.append(f"{path}:{node.lineno}: async def {node.name}")
    assert not violations, "Blocking I/O in async functions:\n" + "\n".join(
        violations[:50]
    )
