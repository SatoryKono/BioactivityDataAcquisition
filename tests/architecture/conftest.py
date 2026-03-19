"""Session-scoped caches for architecture tests.

Eliminates redundant file I/O and AST parsing across ~36 architecture test
files that independently call rglob("*.py") + ast.parse() on the same
source tree.  A single session-scoped parse pass (~1.5 s) replaces
~10 000 redundant reads/parses (~10.5 s saving).
"""

from __future__ import annotations

import ast
from pathlib import Path
import pickle

import pytest


_CACHE_VERSION = 1


def _cache_dir(project_root: Path) -> Path:
    """Return persistent cache directory for architecture fixture artifacts."""
    cache_dir = project_root / ".pytest_cache" / "bioetl_architecture"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_key(path: Path) -> str:
    """Normalize cache keys to stable POSIX paths."""
    return path.as_posix()


def _path_signature(path: Path) -> tuple[int, int]:
    """Return a cheap file signature based on mtime and size."""
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def _load_pickle_cache(path: Path) -> dict[str, object]:
    """Load a pickle cache payload or return an empty payload on mismatch."""
    try:
        payload = pickle.loads(path.read_bytes())
    except (OSError, EOFError, pickle.PickleError, AttributeError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    if payload.get("version") != _CACHE_VERSION:
        return {}
    return payload


def _write_pickle_cache(path: Path, payload: dict[str, object]) -> None:
    """Write pickle cache payload atomically enough for local pytest runs."""
    path.write_bytes(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))


def _build_text_cache(
    paths: list[Path],
    cache_file: Path,
) -> dict[Path, str]:
    """Reuse cached file contents for unchanged files across pytest sessions."""
    payload = _load_pickle_cache(cache_file)
    cached_entries = payload.get("entries", {})
    if not isinstance(cached_entries, dict):
        cached_entries = {}

    result: dict[Path, str] = {}
    updated_entries: dict[str, object] = {}
    changed = False

    for path in paths:
        key = _cache_key(path)
        signature = _path_signature(path)
        entry = cached_entries.get(key)
        if isinstance(entry, dict) and tuple(entry.get("sig", ())) == signature:
            text = entry.get("text")
            if isinstance(text, str):
                result[path] = text
                updated_entries[key] = entry
                continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            changed = True
            continue

        result[path] = text
        updated_entries[key] = {"sig": signature, "text": text}
        changed = True

    if changed or len(updated_entries) != len(cached_entries):
        _write_pickle_cache(
            cache_file,
            {"version": _CACHE_VERSION, "entries": updated_entries},
        )
    return result


def _build_ast_cache(
    text_cache: dict[Path, str],
    cache_file: Path,
) -> dict[Path, ast.Module]:
    """Reuse cached ASTs for unchanged files across pytest sessions."""
    payload = _load_pickle_cache(cache_file)
    cached_entries = payload.get("entries", {})
    if not isinstance(cached_entries, dict):
        cached_entries = {}

    result: dict[Path, ast.Module] = {}
    updated_entries: dict[str, object] = {}
    changed = False

    for path, content in text_cache.items():
        key = _cache_key(path)
        signature = _path_signature(path)
        entry = cached_entries.get(key)
        if isinstance(entry, dict) and tuple(entry.get("sig", ())) == signature:
            tree = entry.get("ast")
            if isinstance(tree, ast.Module):
                result[path] = tree
                updated_entries[key] = entry
                continue

        try:
            tree = ast.parse(content)
        except SyntaxError:
            changed = True
            continue

        result[path] = tree
        updated_entries[key] = {"sig": signature, "ast": tree}
        changed = True

    if changed or len(updated_entries) != len(cached_entries):
        _write_pickle_cache(
            cache_file,
            {"version": _CACHE_VERSION, "entries": updated_entries},
        )
    return result


# ---------------------------------------------------------------------------
# Source file caches (src/bioetl/**)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def src_python_files(src_dir: Path) -> list[Path]:
    """Sorted list of all *.py files under src/bioetl/ (no __pycache__)."""
    bioetl = src_dir / "bioetl"
    return sorted(p for p in bioetl.rglob("*.py") if "__pycache__" not in p.parts)


@pytest.fixture(scope="session")
def source_content_cache(
    project_root: Path,
    src_python_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every source file, keyed by absolute Path."""
    cache_file = _cache_dir(project_root) / "source_content_cache.pkl"
    return _build_text_cache(src_python_files, cache_file)


@pytest.fixture(scope="session")
def source_ast_cache(
    project_root: Path,
    source_content_cache: dict[Path, str],
) -> dict[Path, ast.Module]:
    """Parsed AST of every source file, keyed by absolute Path."""
    cache_file = _cache_dir(project_root) / "source_ast_cache.pkl"
    return _build_ast_cache(source_content_cache, cache_file)


# ---------------------------------------------------------------------------
# Test file caches (tests/**)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_python_files(project_root: Path) -> list[Path]:
    """Sorted list of all *.py test files (no __pycache__, no worktrees)."""
    tests_root = project_root / "tests"
    return sorted(
        p
        for p in tests_root.rglob("*.py")
        if "__pycache__" not in p.parts and ".worktrees" not in p.parts
    )


@pytest.fixture(scope="session")
def test_content_cache(
    project_root: Path,
    test_python_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every test file."""
    cache_file = _cache_dir(project_root) / "test_content_cache.pkl"
    return _build_text_cache(test_python_files, cache_file)


@pytest.fixture(scope="session")
def test_ast_cache(
    project_root: Path,
    test_content_cache: dict[Path, str],
) -> dict[Path, ast.Module]:
    """Parsed AST of every test file."""
    cache_file = _cache_dir(project_root) / "test_ast_cache.pkl"
    return _build_ast_cache(test_content_cache, cache_file)
