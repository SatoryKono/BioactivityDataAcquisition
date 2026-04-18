"""Session-scoped caches for architecture tests.

Eliminates redundant file I/O and AST parsing across ~36 architecture test
files that independently call rglob("*.py") + ast.parse() on the same
source tree.  A single session-scoped parse pass (~1.5 s) replaces
~10 000 redundant reads/parses (~10.5 s saving).
"""

from __future__ import annotations

import ast
from collections.abc import Callable
import os
from pathlib import Path
import subprocess

import pytest
import yaml


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


def _build_text_cache(
    paths: list[Path],
) -> dict[Path, str]:
    """Read each file once and share the in-memory cache across the session."""
    result: dict[Path, str] = {}

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        result[path] = text
    return result


def _build_ast_cache(
    text_cache: dict[Path, str],
) -> dict[Path, ast.Module]:
    """Parse each cached text payload once per pytest session."""
    result: dict[Path, ast.Module] = {}

    for path, content in text_cache.items():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        result[path] = tree
    return result


def _build_yaml_cache(
    text_cache: dict[Path, str],
) -> dict[Path, object]:
    """Parse YAML payloads once per pytest session."""
    result: dict[Path, object] = {}

    for path, text in text_cache.items():
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError:
            continue

        result[path] = parsed
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
    src_python_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every source file, keyed by absolute Path."""
    return _build_text_cache(src_python_files)


@pytest.fixture(scope="session")
def source_ast_cache(
    source_content_cache: dict[Path, str],
) -> dict[Path, ast.Module]:
    """Parsed AST of every source file, keyed by absolute Path."""
    return _build_ast_cache(source_content_cache)


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
    test_python_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every test file."""
    return _build_text_cache(test_python_files)


@pytest.fixture(scope="session")
def test_ast_cache(
    test_content_cache: dict[Path, str],
) -> dict[Path, ast.Module]:
    """Parsed AST of every test file."""
    return _build_ast_cache(test_content_cache)


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
    docs_markdown_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every docs markdown file."""
    return _build_text_cache(docs_markdown_files)


@pytest.fixture(scope="session")
def workflow_yaml_files(project_root: Path) -> list[Path]:
    """Sorted list of workflow YAML files under .github/workflows."""
    workflows_root = project_root / ".github" / "workflows"
    return sorted(workflows_root.glob("*.yml")) if workflows_root.exists() else []


@pytest.fixture(scope="session")
def workflow_text_cache(
    workflow_yaml_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every workflow YAML file."""
    return _build_text_cache(workflow_yaml_files)


@pytest.fixture(scope="session")
def workflow_yaml_cache(
    workflow_text_cache: dict[Path, str],
) -> dict[Path, object]:
    """Parsed YAML payload of every workflow file."""
    return _build_yaml_cache(workflow_text_cache)


@pytest.fixture(scope="session")
def config_yaml_files(project_root: Path) -> list[Path]:
    """Sorted list of YAML files under configs/."""
    configs_root = project_root / "configs"
    return sorted(
        p for p in configs_root.rglob("*.yaml") if "__pycache__" not in p.parts
    )


@pytest.fixture(scope="session")
def config_text_cache(
    config_yaml_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every config YAML file."""
    return _build_text_cache(config_yaml_files)


@pytest.fixture(scope="session")
def config_yaml_cache(
    config_text_cache: dict[Path, str],
) -> dict[Path, object]:
    """Parsed YAML payload of every config file."""
    return _build_yaml_cache(config_text_cache)


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
