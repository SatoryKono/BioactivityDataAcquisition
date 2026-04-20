from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "bioetl"


def _docstring_quote_prefix(stripped: str) -> str | None:
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return stripped[:3]
    return None


def _docstring_closed_on_line(stripped: str, docstring_char: str) -> bool:
    return stripped.endswith(docstring_char) or docstring_char in stripped[1:]


def _strip_inline_comment(line: str, *, marker: str) -> str:
    return line.split(marker)[0] if marker in line else line


def _strip_docstrings_and_comments(text: str) -> dict[int, str]:
    """Return mapping of line_number -> code_only for non-docstring, non-comment lines."""
    result: dict[int, str] = {}
    in_docstring = False
    docstring_char = ""
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if in_docstring:
            if _docstring_closed_on_line(stripped, docstring_char):
                in_docstring = False
            continue
        quote_prefix = _docstring_quote_prefix(stripped)
        if quote_prefix is not None:
            docstring_char = quote_prefix
            if stripped.count(docstring_char) == 1:
                in_docstring = True
            continue
        if stripped.startswith("#"):
            continue
        # Remove inline comments
        code_part = _strip_inline_comment(line, marker="  #")
        result[i] = code_part
    return result


def test_no_sentinel_values(source_content_cache: dict) -> None:
    # Only match assignment sentinels, not mentions in strings/docs
    rx = re.compile(r"=\s*-1\b|=\s*9999\b")
    # UPPER_CASE constants may legitimately use -1 (e.g., zstd thread config)
    const_assign = re.compile(r"^\s*[A-Z_]+\s*=")
    violations: list[str] = []
    for path, text in source_content_cache.items():
        code_lines = _strip_docstrings_and_comments(text)
        for i, code in code_lines.items():
            if rx.search(code) and not const_assign.match(code):
                violations.append(f"{path}:{i}: {text.splitlines()[i - 1].strip()}")
    assert not violations, "Sentinel values found:\n" + "\n".join(violations[:50])


@pytest.mark.slow
def test_no_hardcoded_secrets() -> None:
    baseline_path = REPO_ROOT / ".secrets.baseline"
    if not baseline_path.exists():
        raise AssertionError("Missing .secrets.baseline for detect-secrets scan")

    result = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", str(SRC)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "detect-secrets scan failed:\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    try:
        scan_output = json.loads(result.stdout)
        baseline_output = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError("detect-secrets output is not valid JSON") from exc

    baseline_hashes = {
        finding.get("hashed_secret")
        for findings in baseline_output.get("results", {}).values()
        for finding in findings
    }

    violations: list[str] = []
    for file_path, findings in scan_output.get("results", {}).items():
        for finding in findings:
            hashed_secret = finding.get("hashed_secret")
            if hashed_secret and hashed_secret in baseline_hashes:
                continue
            line_number = finding.get("line_number", "?")
            secret_type = finding.get("type", "Secret")
            violations.append(f"{file_path}:{line_number}: {secret_type}")

    assert not violations, (
        "Potential secrets detected. Update .secrets.baseline if false positives:\n"
        + "\n".join(violations[:50])
    )


def test_no_print_in_production(source_content_cache: dict) -> None:
    violations: list[str] = []
    for path, text in source_content_cache.items():
        if path.match("src/bioetl/interfaces/cli/*") or "interfaces/cli" in str(path):
            continue
        for i, line in enumerate(text.splitlines(), 1):
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
        quote_prefix = _docstring_quote_prefix(stripped)
        if quote_prefix is not None:
            ds_quote = quote_prefix
            if stripped.count(ds_quote) < 2:
                in_docstring = True
            continue
        # Remove inline comments
        code_part = line.split("#")[0]
        lines.append(code_part)
    return "\n".join(lines)


def _iter_async_function_defs(tree: ast.AST) -> list[ast.AsyncFunctionDef]:
    return [
        node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
    ]


def _async_function_uses_blocking_io(node: ast.AsyncFunctionDef, *, source: str) -> bool:
    segment = ast.get_source_segment(source, node) or ""
    if "run_in_executor" in segment or "to_thread" in segment:
        return False
    code_only = _extract_code_only(segment)
    return any(x in code_only for x in ["open(", "requests.", "urllib"])


def test_no_blocking_io_in_async(
    source_ast_cache: dict,
    source_content_cache: dict,
) -> None:
    violations: list[str] = []
    for path, tree in source_ast_cache.items():
        source = source_content_cache[path]
        for node in _iter_async_function_defs(tree):
            if _async_function_uses_blocking_io(node, source=source):
                violations.append(f"{path}:{node.lineno}: async def {node.name}")
    assert not violations, "Blocking I/O in async functions:\n" + "\n".join(
        violations[:50]
    )
