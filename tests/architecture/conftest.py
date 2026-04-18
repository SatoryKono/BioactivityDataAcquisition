"""Session-scoped caches for architecture tests.

Eliminates redundant file I/O and AST parsing across ~36 architecture test
files that independently call rglob("*.py") + ast.parse() on the same
source tree.  A single session-scoped parse pass (~1.5 s) replaces
~10 000 redundant reads/parses (~10.5 s saving).
"""

from __future__ import annotations

import ast
from collections.abc import Callable
import hashlib
import os
from pathlib import Path
import pickle
import subprocess
import tempfile

import pytest
import yaml


_CACHE_VERSION = 2


def _list_python_files(root: Path) -> list[Path]:
    """Collect Python files under ``root`` faster than ``Path.rglob`` on /mnt/*."""
    python_files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in {"__pycache__", ".worktrees"}
        ]
        current_path = Path(current_root)
        for filename in filenames:
            if filename.endswith(".py"):
                python_files.append(current_path / filename)
    return sorted(python_files)


def _cache_dir(project_root: Path) -> Path:
    """Return persistent cache directory for architecture fixture artifacts."""
    cache_dir = project_root / ".pytest_cache" / "bioetl_architecture"
    worker_id = os.getenv("PYTEST_XDIST_WORKER")
    if worker_id:
        # Isolate per-worker cache writes under xdist to avoid file lock contention
        # on Windows when multiple workers update the same pickle files.
        cache_dir = cache_dir / worker_id
    if _ensure_cache_dir_writable(cache_dir):
        return cache_dir

    project_key = hashlib.blake2b(
        str(project_root).encode("utf-8"),
        digest_size=8,
    ).hexdigest()
    fallback_dir = (
        Path(tempfile.gettempdir()) / "bioetl_architecture_cache" / project_key
    )
    if worker_id:
        fallback_dir = fallback_dir / worker_id
    fallback_dir.mkdir(parents=True, exist_ok=True)
    return fallback_dir


def _ensure_cache_dir_writable(path: Path) -> bool:
    """Return True when the cache directory exists and accepts a tiny probe write."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _cache_key(path: Path) -> str:
    """Normalize cache keys to stable POSIX paths."""
    return path.as_posix()


def _path_signature(path: Path) -> tuple[int, int]:
    """Return a cheap file signature based on mtime and size."""
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def _text_signature(text: str) -> tuple[int, str]:
    """Return a content-derived signature for parse caches.

    Using the text payload avoids stale AST/YAML reuse when a file's parsed
    cache survives but the raw text cache was refreshed independently.
    """
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()
    return len(text), digest


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
        signature = _text_signature(content)
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


def _build_yaml_cache(
    text_cache: dict[Path, str],
    cache_file: Path,
) -> dict[Path, object]:
    """Reuse parsed YAML payloads for unchanged files across pytest sessions."""
    payload = _load_pickle_cache(cache_file)
    cached_entries = payload.get("entries", {})
    if not isinstance(cached_entries, dict):
        cached_entries = {}

    result: dict[Path, object] = {}
    updated_entries: dict[str, object] = {}
    changed = False

    for path, text in text_cache.items():
        key = _cache_key(path)
        signature = _text_signature(text)
        entry = cached_entries.get(key)
        if isinstance(entry, dict) and tuple(entry.get("sig", ())) == signature:
            if "yaml" in entry:
                result[path] = entry["yaml"]
                updated_entries[key] = entry
                continue

        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError:
            changed = True
            continue

        result[path] = parsed
        updated_entries[key] = {"sig": signature, "yaml": parsed}
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
    return _list_python_files(bioetl)


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
    return _list_python_files(tests_root)


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


# ---------------------------------------------------------------------------
# Documentation / workflow / config text caches
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def docs_markdown_files(project_root: Path) -> list[Path]:
    """Sorted list of all markdown files under docs/."""
    docs_root = project_root / "docs"
    return sorted(p for p in docs_root.rglob("*.md") if "__pycache__" not in p.parts)


@pytest.fixture(scope="session")
def docs_text_cache(
    project_root: Path,
    docs_markdown_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every docs markdown file."""
    cache_file = _cache_dir(project_root) / "docs_text_cache.pkl"
    return _build_text_cache(docs_markdown_files, cache_file)


@pytest.fixture(scope="session")
def workflow_yaml_files(project_root: Path) -> list[Path]:
    """Sorted list of workflow YAML files under .github/workflows."""
    workflows_root = project_root / ".github" / "workflows"
    return sorted(workflows_root.glob("*.yml")) if workflows_root.exists() else []


@pytest.fixture(scope="session")
def workflow_text_cache(
    project_root: Path,
    workflow_yaml_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every workflow YAML file."""
    cache_file = _cache_dir(project_root) / "workflow_text_cache.pkl"
    return _build_text_cache(workflow_yaml_files, cache_file)


@pytest.fixture(scope="session")
def workflow_yaml_cache(
    project_root: Path,
    workflow_text_cache: dict[Path, str],
) -> dict[Path, object]:
    """Parsed YAML payload of every workflow file."""
    cache_file = _cache_dir(project_root) / "workflow_yaml_cache.pkl"
    return _build_yaml_cache(workflow_text_cache, cache_file)


@pytest.fixture(scope="session")
def config_yaml_files(project_root: Path) -> list[Path]:
    """Sorted list of YAML files under configs/."""
    configs_root = project_root / "configs"
    return sorted(
        p for p in configs_root.rglob("*.yaml") if "__pycache__" not in p.parts
    )


@pytest.fixture(scope="session")
def config_text_cache(
    project_root: Path,
    config_yaml_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every config YAML file."""
    cache_file = _cache_dir(project_root) / "config_text_cache.pkl"
    return _build_text_cache(config_yaml_files, cache_file)


@pytest.fixture(scope="session")
def config_yaml_cache(
    project_root: Path,
    config_text_cache: dict[Path, str],
) -> dict[Path, object]:
    """Parsed YAML payload of every config file."""
    cache_file = _cache_dir(project_root) / "config_yaml_cache.pkl"
    return _build_yaml_cache(config_text_cache, cache_file)


@pytest.fixture(scope="session")
def cached_subprocess_run() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run subprocess commands once per unique command/timeout/cwd in session."""
    cache: dict[
        tuple[tuple[str, ...], float | None, str | None],
        subprocess.CompletedProcess[str],
    ] = {}

    def _run(
        command: list[str],
        *,
        timeout: float | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        key = (
            tuple(command),
            timeout,
            str(cwd) if cwd is not None else None,
        )
        if key not in cache:
            cache[key] = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                check=False,
            )
        return cache[key]

    return _run
