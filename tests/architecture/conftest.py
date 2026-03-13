"""Session-scoped caches for architecture tests.

Eliminates redundant file I/O and AST parsing across ~36 architecture test
files that independently call rglob("*.py") + ast.parse() on the same
source tree.  A single session-scoped parse pass (~1.5 s) replaces
~10 000 redundant reads/parses (~10.5 s saving).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Source file caches (src/bioetl/**)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def src_python_files(src_dir: Path) -> list[Path]:
    """Sorted list of all *.py files under src/bioetl/ (no __pycache__)."""
    bioetl = src_dir / "bioetl"
    return sorted(p for p in bioetl.rglob("*.py") if "__pycache__" not in p.parts)


@pytest.fixture(scope="session")
def source_content_cache(src_python_files: list[Path]) -> dict[Path, str]:
    """Raw UTF-8 text of every source file, keyed by absolute Path."""
    cache: dict[Path, str] = {}
    for f in src_python_files:
        try:
            cache[f] = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass
    return cache


@pytest.fixture(scope="session")
def source_ast_cache(
    source_content_cache: dict[Path, str],
) -> dict[Path, ast.Module]:
    """Parsed AST of every source file, keyed by absolute Path."""
    cache: dict[Path, ast.Module] = {}
    for path, content in source_content_cache.items():
        try:
            cache[path] = ast.parse(content)
        except SyntaxError:
            pass
    return cache


# ---------------------------------------------------------------------------
# Test file caches (tests/**)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_python_files() -> list[Path]:
    """Sorted list of all *.py test files (no __pycache__, no worktrees)."""
    tests_root = Path("tests")
    return sorted(
        p
        for p in tests_root.rglob("*.py")
        if "__pycache__" not in p.parts and ".worktrees" not in p.parts
    )


@pytest.fixture(scope="session")
def test_content_cache(test_python_files: list[Path]) -> dict[Path, str]:
    """Raw UTF-8 text of every test file."""
    cache: dict[Path, str] = {}
    for f in test_python_files:
        try:
            cache[f] = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass
    return cache


@pytest.fixture(scope="session")
def test_ast_cache(test_content_cache: dict[Path, str]) -> dict[Path, ast.Module]:
    """Parsed AST of every test file."""
    cache: dict[Path, ast.Module] = {}
    for path, content in test_content_cache.items():
        try:
            cache[path] = ast.parse(content)
        except SyntaxError:
            pass
    return cache
