# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Session-scoped caches for architecture tests.

Eliminates redundant file I/O and AST parsing across ~36 architecture test
files that independently call rglob("*.py") + ast.parse() on the same
source tree.  A single session-scoped parse pass (~1.5 s) replaces
~10 000 redundant reads/parses (~10.5 s saving).
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
from typing import cast
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite
from tests.helpers.compat_shim_guards import ImportRecord, build_import_records

import pytest
import yaml

# Import governance report function for caching
from scripts.engineering.qa.report_test_governance_audit import (
    collect_test_governance_report,
)

_MIN_PARALLEL_CACHE_FILES = 128
_DEFAULT_CACHE_WORKERS = 8
_MAX_CACHE_WORKERS = 16
_MAX_CACHE_WORKERS_NETWORK = 4
_ARCHITECTURE_CACHE_VERSION = "v3"
_ARCHITECTURE_CACHE_DIR = Path(
    os.environ.get(
        "BIOETL_ARCHITECTURE_CACHE_DIR",
        str(Path(tempfile.gettempdir()) / "bioetl-architecture-cache"),
    )
)
# Large mounted-worktree text caches are faster to rebuild in-memory once per
# session than to re-stat and pickle under the global per-test timeout.
_TEXT_CACHE_NAMES_WITHOUT_DISK = frozenset(
    {
        "docs-text",
        "source-content",
        "test-content",
    }
)
_WINDOWS_PYCHARM_SUBPROCESS_TIMEOUT_SECONDS = 180.0
_MOUNTED_WORKTREE_SUBPROCESS_TIMEOUT_SECONDS = 180.0


def _is_windows_pycharm_pytest_runner() -> bool:
    """Return whether tests are running from the Windows PyCharm pytest runner."""
    if not sys.platform.startswith("win"):
        return False
    if os.environ.get("PYCHARM_HOSTED") == "1":
        return True
    return any("_jb_pytest_runner.py" in arg.replace("\\", "/") for arg in sys.argv)


def _effective_subprocess_timeout(timeout: float | None) -> float | None:
    """Give repo-wide scanners enough room on known slow filesystem surfaces."""
    if (
        timeout is not None
        and _is_windows_pycharm_pytest_runner()
        and timeout < _WINDOWS_PYCHARM_SUBPROCESS_TIMEOUT_SECONDS
    ):
        # Repo-backed scanner subprocesses can stall unpredictably on mixed
        # Windows cloud-synced checkouts when launched from the PyCharm runner.
        return _WINDOWS_PYCHARM_SUBPROCESS_TIMEOUT_SECONDS
    if (
        timeout is not None
        and sys.platform.startswith("linux")
        and Path(__file__).resolve().is_relative_to("/mnt")
        and timeout < _MOUNTED_WORKTREE_SUBPROCESS_TIMEOUT_SECONDS
    ):
        return _MOUNTED_WORKTREE_SUBPROCESS_TIMEOUT_SECONDS
    return timeout


# Directories that must never be descended into when collecting docs markdown.
# ``site`` is the local MkDocs HTML build (``docs/site/``, gitignored) and can
# contain hundreds of non-markdown files; walking it on cloud-synced Windows
# checkouts routinely blows the default 60s pytest timeout during fixture setup.
_DOCS_MARKDOWN_WALK_SKIP_DIRNAMES = frozenset(
    {
        "__pycache__",
        ".git",
        ".worktrees",
        "site",
    }
)


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


def _discover_git_toplevel(start: Path) -> Path | None:
    """Locate a git worktree root without spawning git.

    Spawning ``git rev-parse`` from a temp directory under a Windows cloud-synced
    checkout can hang in pipe reader threads even with a timeout (pytest-timeout
    then kills the whole test). Walking parents for a ``.git`` entry is enough to
    decide whether ``git ls-files`` is applicable, and respects
    ``GIT_CEILING_DIRECTORIES`` the same way the test suite isolates tmp trees.
    """
    ceilings: set[Path] = set()
    for part in os.environ.get("GIT_CEILING_DIRECTORIES", "").split(os.pathsep):
        cleaned = part.strip()
        if not cleaned:
            continue
        try:
            ceilings.add(Path(cleaned).resolve())
        except OSError:
            continue

    try:
        current = start.resolve()
    except OSError:
        return None
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        try:
            if (candidate / ".git").exists():
                return candidate
        except OSError:
            return None
        if candidate in ceilings:
            break
        if candidate.parent == candidate:
            break
    return None


def _list_markdown_files_via_git(root: Path) -> list[Path] | None:
    """Return tracked ``*.md`` under ``root`` via git, or ``None`` on failure.

    Prefer this over a full filesystem walk so local generated trees such as
    ``docs/site`` are never enumerated. Paths are joined without per-file
    ``exists()``/``resolve()`` probes (those are extremely expensive on
    cloud-synced drives and were a prior timeout source).
    """
    if not root.exists():
        return []

    git_root = _discover_git_toplevel(root)
    if git_root is None:
        return None

    try:
        rel_root = root.resolve().relative_to(git_root.resolve()).as_posix()
    except (OSError, ValueError):
        return None

    creationflags = 0
    if sys.platform.startswith("win") and hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        result = subprocess.run(
            ["git", "-C", str(git_root), "ls-files", "-z", "--", rel_root],
            capture_output=True,
            check=False,
            timeout=15,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            return None

        markdown_files: list[Path] = []
        for entry in result.stdout.split(b"\0"):
            if not entry.endswith(b".md"):
                continue
            rel = entry.decode("utf-8", errors="surrogateescape")
            markdown_files.append(git_root / rel)
        return sorted(markdown_files)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, ValueError):
        return None


def _list_markdown_files_via_walk(root: Path) -> list[Path]:
    """Filesystem walk fallback that prunes generated/build directories."""
    markdown_files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in _DOCS_MARKDOWN_WALK_SKIP_DIRNAMES
        ]
        current_path = Path(current_root)
        for filename in filenames:
            if filename.endswith(".md"):
                markdown_files.append(current_path / filename)
    return sorted(markdown_files)


def _list_markdown_files(root: Path) -> list[Path]:
    """Collect Markdown files under ``root`` faster than ``Path.rglob`` on /mnt/*."""
    git_listed = _list_markdown_files_via_git(root)
    if git_listed is not None:
        return git_listed
    return _list_markdown_files_via_walk(root)


def _cache_worker_count(total_files: int) -> int:
    """Choose a conservative worker count for mounted-worktree file reads."""
    # Detect network drives on Windows and disable threading entirely
    if os.name == "nt":
        try:
            import ctypes

            drive = os.path.splitdrive(os.getcwd())[0] + "\\"
            is_network_drive = (
                ctypes.windll.kernel32.GetDriveTypeW(drive) == 4
            )  # DRIVE_REMOTE
            if is_network_drive:
                return 1  # Single-threaded for network drives
        except Exception:
            pass

    if total_files < _MIN_PARALLEL_CACHE_FILES:
        return 1

    cpu_count = os.cpu_count() or _DEFAULT_CACHE_WORKERS
    return min(total_files, _MAX_CACHE_WORKERS, max(_DEFAULT_CACHE_WORKERS, cpu_count))


def _read_text_cache_entry(path: Path) -> tuple[Path, str | None]:
    """Read one UTF-8 text payload for the session cache."""
    try:
        with path.open(encoding="utf-8", errors="strict") as f:
            return path, f.read()
    except (OSError, UnicodeDecodeError):
        return path, None


def _cache_signature(paths: list[Path]) -> str:
    """Build a stable cache signature from file paths and stat metadata."""
    digest = hashlib.sha256(_ARCHITECTURE_CACHE_VERSION.encode("utf-8"))

    for path in paths:
        try:
            stat_result = path.stat()
        except OSError:
            continue

        digest.update(str(path).encode("utf-8", errors="ignore"))
        digest.update(str(stat_result.st_mtime_ns).encode("ascii"))
        digest.update(str(stat_result.st_size).encode("ascii"))

    return digest.hexdigest()


def _cache_file_path(cache_name: str, signature: str) -> Path:
    """Return the on-disk cache path for one architecture helper cache."""
    return _ARCHITECTURE_CACHE_DIR / f"{cache_name}-{signature}.pkl"


def _load_disk_cache(
    cache_name: str,
    paths: list[Path],
) -> object | None:
    """Load a persisted cache snapshot when the file manifest still matches."""
    cache_path = _cache_file_path(cache_name, _cache_signature(paths))
    try:
        with cache_path.open("rb") as handle:
            return pickle.load(handle)
    except (
        OSError,
        EOFError,
        pickle.PickleError,
        AttributeError,
        ImportError,
        ModuleNotFoundError,
        ValueError,
    ):
        return None


def _store_disk_cache(
    cache_name: str,
    paths: list[Path],
    payload: object,
) -> None:
    """Persist a cache snapshot atomically for reuse across reruns."""
    signature = _cache_signature(paths)
    cache_path = _cache_file_path(cache_name, signature)
    temp_path = cache_path.with_name(
        f"{cache_path.name}.{os.getpid()}.{deterministic_uuid_from_callsite('architecture.conftest').hex}.tmp"
    )

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with temp_path.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        try:
            temp_path.replace(cache_path)
        except PermissionError:
            # Another process may have published the same cache payload already.
            if cache_path.exists():
                return
            raise
    except OSError:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _resolve_disk_text_cache_request(
    cache_name: str,
    paths: list[Path] | None,
) -> tuple[str, list[Path]]:
    if paths is None:
        msg = "paths must be provided when cache_name is passed explicitly"
        raise TypeError(msg)
    return cache_name, paths


def _resolve_memory_text_cache_request(
    cache_name_or_paths: list[Path],
) -> tuple[str, list[Path]]:
    return "ad-hoc-text", cache_name_or_paths


def _resolve_ast_cache_request(
    cache_name_or_text_cache: str | dict[Path, str],
    text_cache: dict[Path, str] | None,
) -> tuple[str, dict[Path, str], bool]:
    """Normalize AST-cache inputs.

    Disk persistence is intentionally disabled for AST caches. Parsing in-memory
    once per pytest session is cheaper than pickling large AST dictionaries on
    mounted worktrees, and the latter has been a recurring timeout source for
    architecture tests.
    """
    if isinstance(cache_name_or_text_cache, str):
        cache_name = cache_name_or_text_cache
        if text_cache is None:
            msg = "text_cache must be provided when cache_name is passed explicitly"
            raise TypeError(msg)
        cached_text = text_cache
    else:
        cache_name = "ad-hoc-ast"
        cached_text = cache_name_or_text_cache
    return cache_name, cached_text, False


def _read_text_cache_entries_single_threaded(
    cache_paths: list[Path],
) -> dict[Path, str]:
    result: dict[Path, str] = {}
    for path in cache_paths:
        _, text = _read_text_cache_entry(path)
        if text is not None:
            result[path] = text
    return result


def _read_text_cache_entries_threaded(
    cache_paths: list[Path],
    max_workers: int,
) -> dict[Path, str]:
    result: dict[Path, str] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for path, text in executor.map(_read_text_cache_entry, cache_paths):
            if text is not None:
                result[path] = text
    return result


def _load_disk_cached_payload(
    cache_name: str,
    cache_paths: list[Path],
) -> dict[Path, str] | dict[Path, ast.Module] | None:
    """Load a persisted cache snapshot when available."""
    cached_payload = _load_disk_cache(cache_name, cache_paths)
    if isinstance(cached_payload, dict):
        return cached_payload
    return None


def _write_disk_cached_payload(
    cache_name: str,
    cache_paths: list[Path],
    payload: dict[Path, str] | dict[Path, ast.Module],
    use_disk_cache: bool,
) -> None:
    """Persist the computed cache payload when disk caching is enabled."""
    if use_disk_cache:
        _store_disk_cache(cache_name, cache_paths, payload)


def _parse_ast_cache_entry(item: tuple[Path, str]) -> tuple[Path, ast.Module | None]:
    """Parse a single source file into an AST tree when possible."""
    path, content = item
    try:
        return path, ast.parse(content)
    except SyntaxError:
        return path, None


def _read_ast_cache_entries(
    cached_text: dict[Path, str],
    _max_workers: int,
) -> dict[Path, ast.Module]:
    """Parse cached text payloads into ASTs.

    AST parsing is kept single-threaded here. Threaded shutdown on the current
    Python/WSL stack has proven less stable than the marginal speedup it offers
    for architecture fixtures, and fixture timeouts are more expensive than the
    small parse cost.
    """
    result: dict[Path, ast.Module] = {}
    for path, content in cached_text.items():
        parsed_path, tree = _parse_ast_cache_entry((path, content))
        if tree is not None:
            result[parsed_path] = tree
    return result


def _build_text_cache(
    cache_name_or_paths: str | list[Path],
    paths: list[Path] | None = None,
) -> dict[Path, str]:
    """Read each file once and share the in-memory cache across the session."""
    explicit_cache_name = isinstance(cache_name_or_paths, str)
    use_disk_cache = (
        explicit_cache_name
        and cache_name_or_paths not in _TEXT_CACHE_NAMES_WITHOUT_DISK
    )
    if explicit_cache_name:
        cache_name, cache_paths = _resolve_disk_text_cache_request(
            cache_name_or_paths,
            paths,
        )
    else:
        cache_name, cache_paths = _resolve_memory_text_cache_request(
            cache_name_or_paths
        )
    cached_payload = (
        _load_disk_cached_payload(cache_name, cache_paths) if use_disk_cache else None
    )
    if cached_payload is not None:
        return cast(dict[Path, str], cached_payload)

    max_workers = _cache_worker_count(len(cache_paths))
    if max_workers == 1:
        result = _read_text_cache_entries_single_threaded(cache_paths)
    else:
        result = _read_text_cache_entries_threaded(cache_paths, max_workers)
    _write_disk_cached_payload(cache_name, cache_paths, result, use_disk_cache)
    return result


def _build_ast_cache(
    cache_name_or_text_cache: str | dict[Path, str],
    text_cache: dict[Path, str] | None = None,
) -> dict[Path, ast.Module]:
    """Parse each cached text payload once per pytest session."""
    cache_name, cached_text, use_disk_cache = _resolve_ast_cache_request(
        cache_name_or_text_cache,
        text_cache,
    )
    cache_paths = list(cached_text)
    cached_payload = _load_disk_cached_payload(cache_name, cache_paths)
    if cached_payload is not None:
        return cast(dict[Path, ast.Module], cached_payload)

    max_workers = _cache_worker_count(len(cache_paths))
    result = _read_ast_cache_entries(cached_text, max_workers)

    _write_disk_cached_payload(cache_name, cache_paths, result, use_disk_cache)
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
    return _build_text_cache("source-content", src_python_files)


@pytest.fixture(scope="session")
def source_ast_cache(
    source_content_cache: dict[Path, str],
) -> dict[Path, ast.Module]:
    """Parsed AST of every source file, keyed by absolute Path."""
    return _build_ast_cache("source-ast", source_content_cache)


@pytest.fixture(scope="session")
def source_import_records(
    source_ast_cache: dict[Path, ast.Module],
) -> tuple[ImportRecord, ...]:
    """Normalized import statements from src/bioetl ASTs, built once per session."""
    return build_import_records(source_ast_cache)


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
    return _build_text_cache("test-content", test_python_files)


@pytest.fixture(scope="session")
def test_ast_cache(
    test_content_cache: dict[Path, str],
) -> dict[Path, ast.Module]:
    """Parsed AST of every test file."""
    return _build_ast_cache("test-ast", test_content_cache)


@pytest.fixture(scope="session")
def test_import_records(
    test_ast_cache: dict[Path, ast.Module],
) -> tuple[ImportRecord, ...]:
    """Normalized import statements from tests ASTs, built once per session."""
    return build_import_records(test_ast_cache)


# ---------------------------------------------------------------------------
# Documentation / workflow / config text caches
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def docs_markdown_files(project_root: Path) -> list[Path]:
    """Sorted list of all markdown files under docs/."""
    docs_root = project_root / "docs"
    return _list_markdown_files(docs_root)


@pytest.fixture(scope="session")
def docs_text_cache(
    docs_markdown_files: list[Path],
) -> dict[Path, str]:
    """Raw UTF-8 text of every docs markdown file."""
    return _build_text_cache("docs-text", docs_markdown_files)


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
    return _build_text_cache("workflow-text", workflow_yaml_files)


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
    return _build_text_cache("config-text", config_yaml_files)


@pytest.fixture(scope="session")
def config_yaml_cache(
    config_text_cache: dict[Path, str],
) -> dict[Path, object]:
    """Parsed YAML payload of every config file."""
    return _build_yaml_cache(config_text_cache)


def _subprocess_cache_dependency_paths(
    command: list[str],
    cwd: Path | None,
) -> list[Path]:
    """Resolve conservative cache dependencies for repo-wide scanner subprocesses."""
    repo_root = Path(__file__).resolve().parents[2]
    dependency_paths = list(_list_python_files(repo_root / "src" / "bioetl"))

    static_files = [
        repo_root / "pyproject.toml",
        repo_root / ".secrets.baseline",
        repo_root / "scripts" / "engineering" / "dev" / "run_mypy.sh",
        repo_root / "scripts" / "engineering" / "dev" / "run_mypy.ps1",
    ]
    dependency_paths.extend(path for path in static_files if path.exists())

    command_text = " ".join(command)
    if "scripts.schema" in command_text and "generate-config-matrix" in command_text:
        dependency_paths.extend(_list_python_files(repo_root / "scripts" / "schema"))
        dependency_paths.extend(
            path
            for path in (
                repo_root / "docs" / "04-reference" / "config_comparison_matrix.csv",
                repo_root / "docs" / "reports" / "generated" / "config-discrepancies-report.md",
                repo_root / "reports" / "quality" / "config-discrepancy-baseline.json",
            )
            if path.exists()
        )
        configs_root = repo_root / "configs"
        if configs_root.exists():
            dependency_paths.extend(
                path
                for path in configs_root.rglob("*.yaml")
                if "__pycache__" not in path.parts
            )

    if (
        cwd is not None
        and cwd.exists()
        and cwd
        not in {
            repo_root,
            repo_root / "src" / "bioetl",
        }
    ):
        dependency_paths.append(cwd)

    return dependency_paths


def _subprocess_cache_path(
    command: list[str],
    *,
    timeout: float | None,
    cwd: Path | None,
    cache_namespace: str,
) -> Path:
    dependency_paths = _subprocess_cache_dependency_paths(command, cwd)
    digest = hashlib.sha256()
    digest.update(_ARCHITECTURE_CACHE_VERSION.encode("utf-8"))
    digest.update(cache_namespace.encode("utf-8"))
    digest.update(repr(tuple(command)).encode("utf-8"))
    digest.update(repr(timeout).encode("utf-8"))
    digest.update(str(cwd.resolve() if cwd is not None else "").encode("utf-8"))
    digest.update(_cache_signature(dependency_paths).encode("ascii"))
    return _ARCHITECTURE_CACHE_DIR / f"subprocess-{digest.hexdigest()}.pkl"


def _load_subprocess_disk_cache(
    cache_path: Path,
    command: list[str],
) -> subprocess.CompletedProcess[str] | None:
    try:
        with cache_path.open("rb") as handle:
            payload = pickle.load(handle)
    except (
        OSError,
        EOFError,
        pickle.PickleError,
        AttributeError,
        ImportError,
        ModuleNotFoundError,
        ValueError,
    ):
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("command") != command:
        return None
    returncode = int(payload.get("returncode", 1))
    if returncode != 0:
        # Do not reuse failing subprocess results across sessions. Drift/update
        # tests can legitimately transition from fail->pass after regenerating
        # artifacts, and a stale negative disk cache should not mask that.
        return None

    return subprocess.CompletedProcess(
        args=command,
        returncode=returncode,
        stdout=str(payload.get("stdout", "")),
        stderr=str(payload.get("stderr", "")),
    )


def _store_subprocess_disk_cache(
    cache_path: Path,
    *,
    command: list[str],
    result: subprocess.CompletedProcess[str],
) -> None:
    if result.returncode != 0:
        return

    temp_path = cache_path.with_name(
        f"{cache_path.name}.{os.getpid()}.{deterministic_uuid_from_callsite('architecture.conftest').hex}.tmp"
    )
    payload = {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with temp_path.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        try:
            temp_path.replace(cache_path)
        except PermissionError:
            if cache_path.exists():
                return
            raise
    except OSError:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _run_cached_subprocess(
    command: list[str],
    *,
    timeout: float | None = None,
    cwd: Path | None = None,
    cache_namespace: str = "architecture-subprocess",
) -> subprocess.CompletedProcess[str]:
    cache_path = _subprocess_cache_path(
        command, timeout=timeout, cwd=cwd, cache_namespace=cache_namespace
    )
    cached = _load_subprocess_disk_cache(cache_path, command)
    if cached is not None:
        return cached

    effective_timeout = _effective_subprocess_timeout(timeout)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=effective_timeout,
        cwd=cwd,
        check=False,
    )
    _store_subprocess_disk_cache(cache_path, command=command, result=result)
    return result


@pytest.fixture(scope="session")
def cached_subprocess_run() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run repo-wide scanner subprocesses once per session with disk-backed reuse."""
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
            cache[key] = _run_cached_subprocess(
                command,
                timeout=timeout,
                cwd=cwd,
            )
        return cache[key]

    return _run


@pytest.fixture(scope="session")
def cached_governance_report() -> Callable[[], dict]:
    """Cache expensive governance report collection once per session."""
    cached_report: dict | None = None

    def _get_report() -> dict:
        nonlocal cached_report
        if cached_report is None:
            # Use the ROOT from the test file location
            root = Path(__file__).resolve().parents[2]
            cached_report = collect_test_governance_report(root)
        return cached_report

    return _get_report
