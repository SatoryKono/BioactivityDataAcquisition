"""Caller-zero governance for the application services package-root lazy facade.

Issue: #3474
"""

from __future__ import annotations

import ast
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT_MODULE = "bioetl.application.services"
_DIRECT_MODULE_IMPORT_SENTINEL = "<module>"
_PACKAGE_ROOT_IMPORT_MARKERS = (
    f"from {PACKAGE_ROOT_MODULE} import",
    f"import {PACKAGE_ROOT_MODULE}",
)
_SEARCH_TIMEOUT_SECONDS = 20.0
_PYTHON_SCAN_TIMEOUT_SECONDS = 60.0
_READ_TIMEOUT_SECONDS = 15.0
_WINDOWS_GIT_CANDIDATES = (
    Path("C:/Program Files/Git/cmd/git.exe"),
    Path("C:/Program Files/Git/bin/git.exe"),
    Path("C:/Program Files (x86)/Git/cmd/git.exe"),
    Path("C:/Program Files (x86)/Git/bin/git.exe"),
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

    python_paths = _candidate_python_paths_via_python_subprocess(root)
    if python_paths is not None:
        return python_paths

    raise AssertionError(
        "Unable to scan application services facade callers without bounded "
        "rg, git grep, or Python subprocess scan. Refusing to fall back to "
        "unbounded in-process Python file reads."
    )


def _candidate_python_paths_via_rg(root: Path) -> tuple[Path, ...] | None:
    pathspec = _repo_relative_pathspec(root)
    if pathspec is None:
        return None

    command = [
        "rg",
        "-l",
        "-F",
        "-e",
        _PACKAGE_ROOT_IMPORT_MARKERS[0],
        "-e",
        _PACKAGE_ROOT_IMPORT_MARKERS[1],
        pathspec,
        "-g",
        "*.py",
    ]
    try:
        completed, stdout = _run_command_with_stdout_file(
            command,
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode not in {0, 1}:
        return None
    return _paths_from_search_output(stdout)


def _candidate_python_paths_via_git_grep(root: Path) -> tuple[Path, ...] | None:
    pathspec = _repo_relative_pathspec(root)
    if pathspec is None:
        return None

    for git_command in _git_commands():
        command = [
            git_command,
            "grep",
            "-l",
            "-F",
            "-e",
            _PACKAGE_ROOT_IMPORT_MARKERS[0],
            "-e",
            _PACKAGE_ROOT_IMPORT_MARKERS[1],
            "--",
            pathspec,
        ]
        try:
            completed, stdout = _run_command_with_stdout_file(
                command,
                timeout=_SEARCH_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

        if completed.returncode in {0, 1}:
            return _paths_from_search_output(stdout)
    return None


def _candidate_python_paths_via_python_subprocess(
    root: Path,
) -> tuple[Path, ...] | None:
    pathspec = _repo_relative_pathspec(root)
    if pathspec is None:
        return None

    command = [
        sys.executable,
        "-c",
        (
            "from pathlib import Path\n"
            "import sys\n"
            "repo_root = Path(sys.argv[1])\n"
            "scan_root = repo_root / sys.argv[2]\n"
            "markers = tuple(sys.argv[3:])\n"
            "for path in sorted(scan_root.rglob('*.py')):\n"
            "    try:\n"
            "        text = path.read_text(encoding='utf-8')\n"
            "    except OSError:\n"
            "        continue\n"
            "    if any(marker in text for marker in markers):\n"
            "        print(path.relative_to(repo_root).as_posix())\n"
        ),
        str(ROOT),
        pathspec,
        *_PACKAGE_ROOT_IMPORT_MARKERS,
    ]
    try:
        completed, stdout = _run_command_with_stdout_file(
            command,
            timeout=_PYTHON_SCAN_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None
    return _paths_from_search_output(stdout)


def _run_command_with_stdout_file(
    command: list[str],
    *,
    timeout: float,
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Run a child process without Windows pipe reader threads."""
    output_path = _temporary_output_path()
    try:
        with output_path.open("w", encoding="utf-8", errors="replace") as stdout_file:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                stdout=stdout_file,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        output = output_path.read_text(encoding="utf-8", errors="replace")
    finally:
        output_path.unlink(missing_ok=True)
    return completed, output


def _temporary_output_path() -> Path:
    handle = tempfile.NamedTemporaryFile(
        prefix="application_services_facade_scan_",
        suffix=".txt",
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def _git_commands() -> tuple[str, ...]:
    commands = ["git"]
    if os.name == "nt":
        commands.extend(str(path) for path in _WINDOWS_GIT_CANDIDATES if path.exists())
    return tuple(dict.fromkeys(commands))


def _repo_relative_pathspec(root: Path) -> str | None:
    try:
        relative = root.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None
    return relative.as_posix() or "."


def _paths_from_search_output(output: str) -> tuple[Path, ...]:
    if not output.strip():
        return ()
    paths: list[Path] = []
    for line in output.splitlines():
        relative_path = line.strip().replace("\\", "/")
        if not relative_path:
            continue
        path = Path(relative_path)
        if path.suffix != ".py":
            continue
        paths.append(path if path.is_absolute() else ROOT / relative_path)
    return tuple(sorted(paths))


def _read_candidate_source(path: Path) -> str | None:
    try:
        source = _read_text_with_subprocess_timeout(path)
    except TimeoutError:  # pragma: no cover - architecture scan safety
        raise AssertionError(f"Timeout reading {path}") from None
    except UnicodeDecodeError as exc:  # pragma: no cover - architecture scan safety
        raise AssertionError(f"Unable to decode {path}: {exc}") from exc

    if not any(marker in source for marker in _PACKAGE_ROOT_IMPORT_MARKERS):
        return None
    return source


def _read_text_with_subprocess_timeout(path: Path) -> str:
    command = [
        sys.executable,
        "-c",
        (
            "from pathlib import Path; "
            "import sys; "
            "sys.stdout.write(Path(sys.argv[1]).read_text(encoding='utf-8'))"
        ),
        str(path),
    ]
    try:
        completed, stdout = _run_command_with_stdout_file(
            command,
            timeout=_READ_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(str(exc)) from exc

    if completed.returncode != 0:
        raise AssertionError(f"Unable to read {path}")

    return stdout


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
