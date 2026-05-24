"""Caller-zero governance for the application services package-root lazy facade.

Issue: #3474
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT_MODULE = "bioetl.application.services"
_DIRECT_MODULE_IMPORT_SENTINEL = "<module>"
_PACKAGE_ROOT_IMPORT_MARKERS = (
    f"from {PACKAGE_ROOT_MODULE} import",
    f"import {PACKAGE_ROOT_MODULE}",
)

EXPECTED_TEST_IMPORTS: dict[str, frozenset[str]] = {}


@lru_cache(maxsize=2)
def _collect_imports(root: Path) -> dict[str, frozenset[str]]:
    """Collect exact imports from ``bioetl.application.services`` under ``root``."""
    paths = _candidate_python_paths(root)
    max_workers = min(32, max(1, os.cpu_count() or 1))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(_collect_imports_for_path, paths)

    return {
        relative_path: frozenset(sorted(imported_names))
        for item in results
        if item is not None
        for relative_path, imported_names in (item,)
    }


def _collect_imports_for_path(path: Path) -> tuple[str, set[str]] | None:
    source = _read_candidate_source(path)
    if source is None:
        return None

    imported_names = _collect_imports_from_tree(_parse_import_tree(path, source))
    if not imported_names:
        return None

    return path.relative_to(ROOT).as_posix(), imported_names


def _candidate_python_paths(root: Path) -> tuple[Path, ...]:
    rg_paths = _candidate_python_paths_via_rg(root)
    if rg_paths is not None:
        return rg_paths

    git_paths = _candidate_python_paths_via_git_grep(root)
    if git_paths is not None:
        return git_paths

    return tuple(
        path for path in sorted(root.rglob("*.py")) if _read_candidate_source(path) is not None
    )


def _candidate_python_paths_via_rg(root: Path) -> tuple[Path, ...] | None:
    rg_binary = shutil.which("rg")
    if rg_binary is None:
        return None

    command = [
        rg_binary,
        "-l",
        "-F",
        "-e",
        _PACKAGE_ROOT_IMPORT_MARKERS[0],
        "-e",
        _PACKAGE_ROOT_IMPORT_MARKERS[1],
        str(root),
        "-g",
        "*.py",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return None

    if completed.returncode not in {0, 1}:
        return None
    return _paths_from_search_output(completed.stdout)


def _candidate_python_paths_via_git_grep(root: Path) -> tuple[Path, ...] | None:
    git_binary = shutil.which("git")
    if git_binary is None:
        return None

    command = [
        git_binary,
        "grep",
        "-l",
        "-e",
        _PACKAGE_ROOT_IMPORT_MARKERS[0],
        "-e",
        _PACKAGE_ROOT_IMPORT_MARKERS[1],
        "--",
        root.as_posix(),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return None

    if completed.returncode not in {0, 1}:
        return None
    return _paths_from_search_output(completed.stdout)


def _paths_from_search_output(output: str) -> tuple[Path, ...]:
    if not output.strip():
        return ()
    return tuple(
        sorted(
            ROOT / relative_path
            for relative_path in output.splitlines()
            if relative_path.strip()
        )
    )


def _read_candidate_source(path: Path) -> str | None:
    def _read_with_timeout() -> str:
        return path.read_text(encoding="utf-8")

    try:
        source = _run_with_timeout(_read_with_timeout, timeout=30.0)
    except TimeoutError:  # pragma: no cover - architecture scan safety
        raise AssertionError(f"Timeout reading {path}") from None
    except UnicodeDecodeError as exc:  # pragma: no cover - architecture scan safety
        raise AssertionError(f"Unable to decode {path}: {exc}") from exc

    if not any(marker in source for marker in _PACKAGE_ROOT_IMPORT_MARKERS):
        return None
    return source


def _run_with_timeout(func, timeout: float):
    """Run a function with a timeout to prevent hangs on locked files."""
    result = None
    exception = None

    def _target():
        nonlocal result, exception
        try:
            result = func()
        except Exception as e:
            exception = e

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise TimeoutError(f"Function did not complete within {timeout} seconds")

    if exception is not None:
        raise exception

    return result


def _parse_import_tree(path: Path, source: str) -> ast.Module:
    try:
        return ast.parse(source)
    except SyntaxError as exc:  # pragma: no cover - architecture scan safety
        raise AssertionError(f"Unable to parse {path}: {exc}") from exc


def _imported_names_from_import(node: ast.Import) -> set[str]:
    return {
        _DIRECT_MODULE_IMPORT_SENTINEL
        for alias in node.names
        if alias.name == PACKAGE_ROOT_MODULE
    }


def _imported_names_from_import_from(node: ast.ImportFrom) -> set[str]:
    if node.module != PACKAGE_ROOT_MODULE:
        return set()
    return {alias.name for alias in node.names}


def _collect_imports_from_tree(tree: ast.Module) -> set[str]:
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(_imported_names_from_import(node))
        elif isinstance(node, ast.ImportFrom):
            imported_names.update(_imported_names_from_import_from(node))
    return imported_names


def test_application_services_package_root_has_zero_first_party_src_callers() -> None:
    """Production code must stay off the package-root lazy compatibility facade."""
    src_imports = _collect_imports(ROOT / "src")
    assert not src_imports, (
        "First-party src imports of bioetl.application.services must stay at zero.\n"
        + "\n".join(
            f"{path}: {sorted(imported_names)}"
            for path, imported_names in sorted(src_imports.items())
        )
    )


def test_application_services_package_root_test_import_inventory_is_frozen() -> None:
    """Test-only compatibility callers must remain explicit until the facade is removed."""
    observed_test_imports = _collect_imports(ROOT / "tests")
    assert observed_test_imports == EXPECTED_TEST_IMPORTS, (
        "Application services package-root compatibility callers drifted.\n"
        "Migrate new callers to canonical owner modules or update the reviewed "
        "caller inventory when intentionally retaining a temporary test seam.\n"
        f"Observed: {observed_test_imports}\n"
        f"Expected: {EXPECTED_TEST_IMPORTS}"
    )


def test_application_services_package_root_inventory_avoids_direct_module_imports() -> (
    None
):
    """Compatibility callers must import explicit symbols, not the whole facade module."""
    observed_test_imports = _collect_imports(ROOT / "tests")
    offenders = {
        path: imported_names
        for path, imported_names in observed_test_imports.items()
        if _DIRECT_MODULE_IMPORT_SENTINEL in imported_names
    }
    assert not offenders, (
        "Tests must import explicit bioetl.application.services symbols instead of "
        "binding the whole lazy facade module.\n"
        + "\n".join(
            f"{path}: {sorted(imported_names)}"
            for path, imported_names in sorted(offenders.items())
        )
    )
