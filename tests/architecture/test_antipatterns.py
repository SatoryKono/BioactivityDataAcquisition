from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path("src/bioetl")


def _py_files() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if "tests" not in p.parts]


def _strip_docstrings_and_comments(text: str) -> dict[int, str]:
    """Return mapping of line_number -> code_only for non-docstring, non-comment lines."""
    result: dict[int, str] = {}
    in_docstring = False
    docstring_char = ""
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if in_docstring:
            if stripped.endswith(docstring_char) or docstring_char in stripped[1:]:
                in_docstring = False
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            docstring_char = stripped[:3]
            if stripped.count(docstring_char) == 1:
                in_docstring = True
            continue
        if stripped.startswith("#"):
            continue
        # Remove inline comments
        code_part = line.split("  #")[0] if "  #" in line else line
        result[i] = code_part
    return result


def test_no_sentinel_values() -> None:
    # Only match assignment sentinels, not mentions in strings/docs
    rx = re.compile(r"=\s*-1\b|=\s*9999\b")
    # UPPER_CASE constants may legitimately use -1 (e.g., zstd thread config)
    const_assign = re.compile(r"^\s*[A-Z_]+\s*=")
    violations: list[str] = []
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        code_lines = _strip_docstrings_and_comments(text)
        for i, code in code_lines.items():
            if rx.search(code) and not const_assign.match(code):
                violations.append(f"{path}:{i}: {text.splitlines()[i - 1].strip()}")
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


def _extract_code_only(func_source: str) -> str:
    """Strip comments and docstrings from function source, keeping only code."""
    lines = []
    in_docstring = False
    ds_quote = ""
    for line in func_source.splitlines():
        stripped = line.strip()
        if in_docstring:
            if ds_quote in stripped:
                in_docstring = False
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            ds_quote = stripped[:3]
            if stripped.count(ds_quote) < 2:
                in_docstring = True
            continue
        # Remove inline comments
        code_part = line.split("#")[0]
        lines.append(code_part)
    return "\n".join(lines)


def test_no_blocking_io_in_async() -> None:
    violations: list[str] = []
    for path in _py_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                segment = ast.get_source_segment(source, node) or ""
                # Allow functions that delegate blocking I/O via run_in_executor
                if "run_in_executor" in segment or "to_thread" in segment:
                    continue
                code_only = _extract_code_only(segment)
                if any(x in code_only for x in ["open(", "requests.", "urllib"]):
                    violations.append(f"{path}:{node.lineno}: async def {node.name}")
    assert not violations, "Blocking I/O in async functions:\n" + "\n".join(
        violations[:50]
    )
