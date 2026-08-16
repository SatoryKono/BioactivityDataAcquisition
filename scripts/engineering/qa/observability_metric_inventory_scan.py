"""Source discovery and AST scanners for observability metric inventory."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import types
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, cast

from scripts.engineering.qa.report_observability_metric_inventory import (
    _CANONICAL_METRIC_RE,
    _DEFAULT_DECLARED_METRIC_DEFINITIONS,
    _DIRECT_COLLECTOR_TERMINAL_METHODS,
    _EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS,
    _INFRASTRUCTURE_PATH_PREFIX,
    _METRIC_MENTION_GREP_CHUNK_SIZE,
    _METRIC_MENTION_GREP_TIMEOUT_SECONDS,
    _NON_METRIC_ALIAS_PREFIXES,
    _PROMETHEUS_ALIAS_SUFFIXES,
    _PROMETHEUS_METRIC_NAME_RE,
    _REGISTERED_SCAN_ROOT,
    _REPO_ROOT,
    _RUNTIME_CANDIDATE_PATH_CACHE,
    _RUNTIME_CANDIDATE_TEXT_CACHE,
    _RUNTIME_EVENT_CANDIDATE_PATH_CACHE,
    _RUNTIME_EVENT_SCAN_MARKERS,
    _RUNTIME_EXCLUDE_PARTS,
    _RUNTIME_METRIC_METHODS,
    _RUNTIME_METRIC_NAME_KEYWORDS,
    _RUNTIME_SCAN_MARKERS,
    _RUNTIME_SCAN_ROOT,
    _SOURCE_TEXT_CACHE,
    _STATIC_RUNTIME_EMITTERS,
    _StartupInfoLike,
    _TEXT_DISCOVERY_TIMEOUT_SECONDS,
    _TEXT_FILE_DISCOVERY_CACHE,
    _TEXT_SUFFIXES,
)

REGISTERED_PROMETHEUS_METRIC_LABELS: dict[str, frozenset[str]] = {}
def _iter_text_files(root: Path) -> list[Path]:
    cache_key = root.as_posix()
    cached = _TEXT_FILE_DISCOVERY_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)
    discovered = _iter_text_files_with_git_ls_files(root)
    if discovered is not None:
        _TEXT_FILE_DISCOVERY_CACHE[cache_key] = tuple(discovered)
        return discovered
    if not root.exists():
        _TEXT_FILE_DISCOVERY_CACHE[cache_key] = ()
        return []
    if root.is_file():
        paths = [root] if root.suffix in _TEXT_SUFFIXES else []
        _TEXT_FILE_DISCOVERY_CACHE[cache_key] = tuple(paths)
        return paths
    discovered = _iter_text_files_with_rg(root)
    if discovered:
        _TEXT_FILE_DISCOVERY_CACHE[cache_key] = tuple(discovered)
        return discovered
    fallback_paths: list[Path] = []
    for dirpath, _, filenames in os.walk(root):
        base = Path(dirpath)
        for filename in filenames:
            path = base / filename
            if path.suffix in _TEXT_SUFFIXES:
                fallback_paths.append(path)
    fallback_paths = sorted(fallback_paths)
    _TEXT_FILE_DISCOVERY_CACHE[cache_key] = tuple(fallback_paths)
    return fallback_paths


def _iter_text_files_with_rg(root: Path) -> list[Path]:
    globs = [
        pattern for suffix in sorted(_TEXT_SUFFIXES) for pattern in ("-g", f"*{suffix}")
    ]
    try:
        result, stdout = _run_text_discovery_command(
            ["rg", "--files", root.as_posix(), *globs],
            timeout=_TEXT_DISCOVERY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode not in {0, 1}:
        return []
    return sorted(
        Path(line)
        for line in stdout.splitlines()
        if line and Path(line).suffix in _TEXT_SUFFIXES
    )


def _iter_text_files_with_git_ls_files(root: Path) -> list[Path] | None:
    pathspec = _repo_relative_pathspec(root)
    if pathspec is None:
        return None
    try:
        tracked_result, tracked_stdout = _run_text_discovery_command(
            ["git", "-C", _REPO_ROOT.as_posix(), "ls-files", "--", pathspec],
            timeout=_TEXT_DISCOVERY_TIMEOUT_SECONDS,
        )
        untracked_result, untracked_stdout = _run_text_discovery_command(
            [
                "git",
                "-C",
                _REPO_ROOT.as_posix(),
                "ls-files",
                "--others",
                "--exclude-standard",
                "--",
                pathspec,
            ],
            timeout=_TEXT_DISCOVERY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if tracked_result.returncode != 0 or untracked_result.returncode != 0:
        return None
    stdout = "\n".join(
        part for part in (tracked_stdout.strip(), untracked_stdout.strip()) if part
    )
    return sorted(
        _REPO_ROOT / line
        for line in stdout.splitlines()
        if line and Path(line).suffix in _TEXT_SUFFIXES
    )


def _run_text_discovery_command(
    command: list[str],
    *,
    timeout: float,
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Capture small discovery output through a bounded subprocess call."""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
        **_hidden_windows_subprocess_kwargs(),
    )
    return result, result.stdout or ""


class _WindowsSubprocessKwargs(TypedDict, total=False):
    creationflags: int
    startupinfo: _StartupInfoLike


def _hidden_windows_subprocess_kwargs(
    *,
    os_name: str = os.name,
    subprocess_module: types.ModuleType = subprocess,
) -> _WindowsSubprocessKwargs:
    if os_name != "nt":
        return {}

    kwargs: _WindowsSubprocessKwargs = {}
    create_no_window = int(getattr(subprocess_module, "CREATE_NO_WINDOW", 0))
    if create_no_window:
        kwargs["creationflags"] = create_no_window

    startupinfo_factory = getattr(subprocess_module, "STARTUPINFO", None)
    if callable(startupinfo_factory):
        startupinfo = cast(_StartupInfoLike, startupinfo_factory())
        startf_use_show_window = int(
            getattr(subprocess_module, "STARTF_USESHOWWINDOW", 0)
        )
        if startf_use_show_window:
            startupinfo.dwFlags = (
                int(getattr(startupinfo, "dwFlags", 0)) | startf_use_show_window
            )
        if hasattr(subprocess_module, "SW_HIDE"):
            startupinfo.wShowWindow = int(getattr(subprocess_module, "SW_HIDE", 0))
        kwargs["startupinfo"] = startupinfo
    return kwargs


def _repo_relative_pathspec(path: Path) -> str | None:
    try:
        common_path = os.path.commonpath(
            [
                os.path.abspath(os.fspath(_REPO_ROOT)),
                os.path.abspath(os.fspath(path)),
            ]
        )
    except ValueError:
        return None
    if os.path.normcase(common_path) != os.path.normcase(
        os.path.abspath(os.fspath(_REPO_ROOT))
    ):
        return None
    relative = os.path.relpath(
        os.path.abspath(os.fspath(path)),
        os.path.abspath(os.fspath(_REPO_ROOT)),
    )
    return "." if relative == "." else relative.replace(os.sep, "/")


def _as_repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _scan_canonical_metric_mentions(
    paths: list[Path],
    repo_root: Path,
) -> dict[str, list[str]]:
    grep_mentions = _scan_canonical_metric_mentions_with_git_grep(paths, repo_root)
    if grep_mentions is not None:
        return grep_mentions
    if (repo_root / ".git").exists():
        rg_mentions = _scan_canonical_metric_mentions_with_rg(paths, repo_root)
        if rg_mentions is not None:
            return rg_mentions
    return _scan_canonical_metric_mentions_via_direct_reads(paths, repo_root)


def _scan_canonical_metric_mentions_via_direct_reads(
    paths: list[Path],
    repo_root: Path,
) -> dict[str, list[str]]:
    mentions: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")  # NOSONAR - path confined
        except (OSError, UnicodeDecodeError):
            continue
        for metric_name in sorted(set(_CANONICAL_METRIC_RE.findall(text))):
            mentions[metric_name].append(_as_repo_relative(path, repo_root))
    return _normalize_mapping_lists(mentions)


def _repo_relative_paths_for_scan(
    paths: list[Path],
    repo_root: Path,
) -> list[str] | None:
    relative_paths: list[str] = []
    for path in paths:
        try:
            relative_paths.append(path.relative_to(repo_root).as_posix())
        except ValueError:
            return None
    return relative_paths


def _append_metric_mentions_from_grep_line(
    mentions: dict[str, list[str]], line: str
) -> None:
    path_text, separator, remainder = line.partition(":")
    if not separator:
        return
    _line_number, separator, text = remainder.partition(":")
    if not separator:
        return
    for metric_name in sorted(set(_CANONICAL_METRIC_RE.findall(text))):
        mentions[metric_name].append(path_text)


def _run_metric_mention_grep(
    *,
    command: list[str],
    cwd: Path | None,
    mentions: dict[str, list[str]],
) -> bool | None:
    """Run one grep chunk. Returns False on hard failure, True on success."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=_METRIC_MENTION_GREP_TIMEOUT_SECONDS,
            cwd=cwd,
            **_hidden_windows_subprocess_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 1:
        return True
    if result.returncode != 0:
        return None
    for line in (result.stdout or "").splitlines():
        _append_metric_mentions_from_grep_line(mentions, line)
    return True


def _scan_metric_mentions_via_command_chunks(
    relative_paths: list[str],
    *,
    command_builder: Callable[[list[str]], list[str]],
    cwd: Path | None = None,
) -> dict[str, list[str]] | None:
    mentions: dict[str, list[str]] = defaultdict(list)
    for index in range(0, len(relative_paths), _METRIC_MENTION_GREP_CHUNK_SIZE):
        chunk = relative_paths[index : index + _METRIC_MENTION_GREP_CHUNK_SIZE]
        outcome = _run_metric_mention_grep(
            command=command_builder(chunk),
            cwd=cwd,
            mentions=mentions,
        )
        if outcome is None:
            return None
    return _normalize_mapping_lists(mentions)


def _scan_canonical_metric_mentions_with_git_grep(
    paths: list[Path],
    repo_root: Path,
) -> dict[str, list[str]] | None:
    """Scan tracked text files without blocking Python on file reads.

    Windows/GDrive checkouts can stall indefinitely on ``Path.read_text`` for
    hydrated or locked documentation files. In real checkouts prefer bounded
    ``git grep`` and keep direct reads only for temporary unit-test trees.
    """
    if not (repo_root / ".git").exists():
        return None

    relative_paths = _repo_relative_paths_for_scan(paths, repo_root)
    if relative_paths is None:
        return None
    if not relative_paths:
        return {}

    def build_command(chunk: list[str]) -> list[str]:
        return [
            "git",
            "-C",
            repo_root.as_posix(),
            "grep",
            "-I",
            "-n",
            "--no-color",
            "bioetl_",
            "--",
            *chunk,
        ]

    return _scan_metric_mentions_via_command_chunks(
        relative_paths, command_builder=build_command
    )


def _scan_canonical_metric_mentions_with_rg(
    paths: list[Path],
    repo_root: Path,
) -> dict[str, list[str]] | None:
    """Fallback bounded scanner when ``git grep`` is unavailable."""
    relative_paths = _repo_relative_paths_for_scan(paths, repo_root)
    if relative_paths is None:
        return None
    if not relative_paths:
        return {}

    def build_command(chunk: list[str]) -> list[str]:
        return [
            "rg",
            "--no-heading",
            "--line-number",
            "--color",
            "never",
            "bioetl_",
            *chunk,
        ]

    return _scan_metric_mentions_via_command_chunks(
        relative_paths, command_builder=build_command, cwd=repo_root
    )


def _normalize_mapping_lists(
    mapping: dict[str, list[str]] | defaultdict[str, list[str]],
) -> dict[str, list[str]]:
    """Return a mapping with deterministically sorted unique list values."""
    return {key: sorted(set(values)) for key, values in sorted(mapping.items())}


def _read_cached_text(path: Path) -> str | None:
    cache_key = path.as_posix()
    cached = _SOURCE_TEXT_CACHE.get(cache_key)
    if cache_key in _SOURCE_TEXT_CACHE:
        return cached
    try:
        text = path.read_text(encoding="utf-8")  # NOSONAR - path confined
    except (OSError, UnicodeDecodeError):
        _SOURCE_TEXT_CACHE[cache_key] = None
        return None
    _SOURCE_TEXT_CACHE[cache_key] = text
    return text


def _read_runtime_candidate_text(path: Path) -> str | None:
    cache_key = f"{path.as_posix()}::runtime"
    cached = _RUNTIME_CANDIDATE_TEXT_CACHE.get(cache_key)
    if cache_key in _RUNTIME_CANDIDATE_TEXT_CACHE:
        return cached
    text = _read_cached_text(path)
    if text is None or not any(marker in text for marker in _RUNTIME_SCAN_MARKERS):
        _RUNTIME_CANDIDATE_TEXT_CACHE[cache_key] = None
        return None
    _RUNTIME_CANDIDATE_TEXT_CACHE[cache_key] = text
    return text


def _read_runtime_event_candidate_text(path: Path) -> str | None:
    cache_key = f"{path.as_posix()}::runtime-event"
    cached = _RUNTIME_CANDIDATE_TEXT_CACHE.get(cache_key)
    if cache_key in _RUNTIME_CANDIDATE_TEXT_CACHE:
        return cached
    text = _read_cached_text(path)
    if text is None or not any(
        marker in text for marker in _RUNTIME_EVENT_SCAN_MARKERS
    ):
        _RUNTIME_CANDIDATE_TEXT_CACHE[cache_key] = None
        return None
    _RUNTIME_CANDIDATE_TEXT_CACHE[cache_key] = text
    return text


def _iter_runtime_candidate_paths(repo_root: Path) -> list[Path]:
    """Return runtime Python files that contain observability scan markers."""
    root = repo_root / _RUNTIME_SCAN_ROOT
    cache_key = root.as_posix()
    cached = _RUNTIME_CANDIDATE_PATH_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)

    discovered = _iter_candidate_paths_with_git_grep(
        root,
        markers=_RUNTIME_SCAN_MARKERS,
        excluded_parts=_RUNTIME_EXCLUDE_PARTS,
    )
    if discovered is not None:
        _RUNTIME_CANDIDATE_PATH_CACHE[cache_key] = tuple(discovered)
        return discovered

    discovered = _iter_runtime_candidate_paths_with_rg(root)
    if discovered:
        _RUNTIME_CANDIDATE_PATH_CACHE[cache_key] = tuple(discovered)
        return discovered

    fallback: list[Path] = []
    for path in _iter_text_files(root):
        if path.suffix != ".py":
            continue
        path_str = path.as_posix()
        if any(excluded in path_str for excluded in _RUNTIME_EXCLUDE_PARTS):
            continue
        if _read_runtime_candidate_text(path) is not None:
            fallback.append(path)
    fallback = sorted(fallback)
    _RUNTIME_CANDIDATE_PATH_CACHE[cache_key] = tuple(fallback)
    return fallback


def _candidate_paths_from_stdout(
    stdout: str,
    *,
    excluded_parts: tuple[str, ...],
) -> list[Path]:
    """Normalize bounded discovery output to filtered Python paths."""
    paths: set[Path] = set()
    for line in stdout.splitlines():
        if not line:
            continue
        raw_path = Path(line)
        path = _REPO_ROOT / raw_path if not raw_path.is_absolute() else raw_path
        path_str = path.as_posix()
        if path.suffix != ".py" or any(
            excluded in path_str for excluded in excluded_parts
        ):
            continue
        paths.add(path)
    return sorted(paths)


def _iter_candidate_paths_with_git_grep(
    root: Path,
    *,
    markers: tuple[str, ...],
    excluded_parts: tuple[str, ...],
) -> list[Path] | None:
    """Use bounded Git-native discovery before touching GDrive files in Python."""
    pathspec = _repo_relative_pathspec(root)
    if pathspec is None:
        return None
    patterns = [pattern for marker in markers for pattern in ("-e", marker)]
    try:
        result, stdout = _run_text_discovery_command(
            [
                "git",
                "-C",
                _REPO_ROOT.as_posix(),
                "grep",
                "--untracked",
                "-I",
                "-l",
                "-F",
                *patterns,
                "--",
                pathspec,
            ],
            timeout=_TEXT_DISCOVERY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode not in {0, 1}:
        return None
    return _candidate_paths_from_stdout(
        stdout,
        excluded_parts=excluded_parts,
    )


def _iter_candidate_paths_with_rg(
    root: Path,
    *,
    markers: tuple[str, ...],
    excluded_parts: tuple[str, ...],
) -> list[Path]:
    """Discover Python candidates with bounded ripgrep before direct reads."""
    regexes = [pattern for marker in markers for pattern in ("-e", re.escape(marker))]
    try:
        result, stdout = _run_text_discovery_command(
            [
                "rg",
                "--files-with-matches",
                "--color",
                "never",
                "--glob",
                "*.py",
                *regexes,
                root.as_posix(),
            ],
            timeout=_TEXT_DISCOVERY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode not in {0, 1}:
        return []
    return _candidate_paths_from_stdout(
        stdout,
        excluded_parts=excluded_parts,
    )


def _iter_runtime_candidate_paths_with_rg(root: Path) -> list[Path]:
    """Discover runtime Python candidates with ripgrep before AST parsing."""
    return _iter_candidate_paths_with_rg(
        root,
        markers=_RUNTIME_SCAN_MARKERS,
        excluded_parts=_RUNTIME_EXCLUDE_PARTS,
    )


def _iter_runtime_event_candidate_paths(repo_root: Path) -> list[Path]:
    """Return runtime Python files that contain observability event markers."""
    root = repo_root / _RUNTIME_SCAN_ROOT
    cache_key = root.as_posix()
    cached = _RUNTIME_EVENT_CANDIDATE_PATH_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)

    discovered = _iter_candidate_paths_with_git_grep(
        root,
        markers=_RUNTIME_EVENT_SCAN_MARKERS,
        excluded_parts=(_INFRASTRUCTURE_PATH_PREFIX,),
    )
    if discovered is not None:
        _RUNTIME_EVENT_CANDIDATE_PATH_CACHE[cache_key] = tuple(discovered)
        return discovered

    discovered = _iter_runtime_event_candidate_paths_with_rg(root)
    if discovered:
        _RUNTIME_EVENT_CANDIDATE_PATH_CACHE[cache_key] = tuple(discovered)
        return discovered

    fallback: list[Path] = []
    for path in _iter_text_files(root):
        if path.suffix != ".py":
            continue
        path_str = path.as_posix()
        if _INFRASTRUCTURE_PATH_PREFIX in path_str:
            continue
        if _read_runtime_event_candidate_text(path) is not None:
            fallback.append(path)
    fallback = sorted(fallback)
    _RUNTIME_EVENT_CANDIDATE_PATH_CACHE[cache_key] = tuple(fallback)
    return fallback


def _iter_runtime_event_candidate_paths_with_rg(root: Path) -> list[Path]:
    """Discover runtime event candidates with ripgrep before AST parsing."""
    return _iter_candidate_paths_with_rg(
        root,
        markers=_RUNTIME_EVENT_SCAN_MARKERS,
        excluded_parts=(_INFRASTRUCTURE_PATH_PREFIX,),
    )


def _collect_runtime_candidate_texts(repo_root: Path) -> list[tuple[Path, str]]:
    """Read runtime candidate texts once and reuse them across metric scans."""
    candidates: list[tuple[Path, str]] = []
    for path in _iter_runtime_candidate_paths(repo_root):
        text = _read_runtime_candidate_text(path)
        if text is None:
            continue
        candidates.append((path, text))
    return candidates


def _module_path_from_import(module_name: str, repo_root: Path) -> Path | None:
    if not module_name.startswith("bioetl."):
        return None
    module_rel = module_name.replace(".", "/")
    module_path = repo_root / "src" / f"{module_rel}.py"
    if module_path.exists():
        return module_path
    package_init = repo_root / "src" / module_rel / "__init__.py"
    if package_init.exists():
        return package_init
    return None


def _collect_module_string_bindings(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")  # NOSONAR - path confined
    except (UnicodeDecodeError, OSError, TimeoutError):
        return {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    bindings: dict[str, str] = {}
    for node in tree.body:
        value_node: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            targets = [node.target]
        if (
            value_node is None
            or not isinstance(value_node, ast.Constant)
            or not isinstance(value_node.value, str)
        ):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value_node.value
    return bindings


def _iter_string_assignments(tree: ast.AST) -> list[tuple[list[ast.expr], str]]:
    assignments: list[tuple[list[ast.expr], str]] = []
    for node in ast.walk(tree):
        value_node: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            targets = [node.target]
        if (
            value_node is None
            or not isinstance(value_node, ast.Constant)
            or not isinstance(value_node.value, str)
        ):
            continue
        assignments.append((targets, value_node.value))
    return assignments


def _resolve_imported_string_bindings(
    tree: ast.AST,
    *,
    repo_root: Path,
    cache: dict[Path, dict[str, str]] | None = None,
) -> dict[str, str]:
    resolved_cache = cache if cache is not None else {}
    bindings: dict[str, str] = {}
    for node in _import_from_nodes(tree):
        relevant_aliases = _imported_string_constant_aliases(node.names)
        if not relevant_aliases:
            continue
        module_bindings = _module_string_bindings(
            node.module,
            repo_root=repo_root,
            cache=resolved_cache,
        )
        if module_bindings is None:
            continue
        _merge_imported_string_aliases(bindings, module_bindings, relevant_aliases)
    return bindings


def _collect_class_attribute_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for class_node in _class_nodes(tree):
        bindings.update(_class_attribute_string_bindings(class_node))
    return bindings


def _collect_repo_class_attribute_bindings(
    candidate_files: list[tuple[Path, str]],
) -> dict[str, str]:
    """Collect string-valued class attributes across runtime scan roots.

    This lets helper modules resolve ``self.METRIC_*`` style references even when
    the concrete string constant is declared on a subclass in another file.
    """
    bindings: dict[str, str] = {}
    for _path, text in candidate_files:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        bindings.update(_collect_class_attribute_bindings(tree))
    return bindings


def _resolve_metric_name_expr(
    node: ast.expr,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return string_bindings.get(node.id) or metric_bindings.get(node.id)
    if isinstance(node, ast.Attribute):
        return attribute_bindings.get(node.attr) or metric_bindings.get(node.attr)
    return None


def _collect_local_string_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for targets, value in _iter_string_assignments(tree):
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value
    return bindings


def _call_method_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _helper_metric_candidates(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
    call_method_name: str | None,
) -> set[str]:
    candidates: set[str] = set()
    if call_method_name == "emit_metric":
        for arg in node.args:
            metric_name = _resolve_metric_name_expr(
                arg,
                string_bindings=string_bindings,
                attribute_bindings=attribute_bindings,
                metric_bindings=metric_bindings,
            )
            if metric_name is not None:
                candidates.add(metric_name)
    for keyword in node.keywords:
        if keyword.value is None:
            continue
        metric_name = _resolve_metric_name_expr(
            keyword.value,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
        if metric_name is None:
            continue
        if keyword.arg in _RUNTIME_METRIC_NAME_KEYWORDS or metric_name.startswith(
            "bioetl_"
        ):
            candidates.add(metric_name)
    return candidates


def _scan_metric_names_in_tree(
    tree: ast.AST,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> tuple[set[str], set[str], set[str]]:
    direct_metric_names: set[str] = set()
    helper_metric_names: set[str] = set()
    alias_metric_names: set[str] = set()

    for call_node in _call_nodes(tree):
        direct_metric_name, helper_candidates = _metric_names_for_call(
            call_node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
        if direct_metric_name is not None:
            direct_metric_names.add(direct_metric_name)
            continue
        _partition_helper_metric_candidates(
            helper_candidates,
            helper_metric_names=helper_metric_names,
            alias_metric_names=alias_metric_names,
        )

    return direct_metric_names, helper_metric_names, alias_metric_names


def _import_from_nodes(tree: ast.AST) -> list[ast.ImportFrom]:
    """Return import-from nodes with concrete module names."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ]


def _looks_like_imported_string_constant_name(name: str) -> bool:
    """Return whether an imported name looks like a UPPER_SNAKE_CASE constant."""
    return any(ch.isalpha() for ch in name) and name.upper() == name


def _imported_string_constant_aliases(aliases: list[ast.alias]) -> list[ast.alias]:
    """Keep only aliases worth resolving as imported string constants."""
    return [
        alias
        for alias in aliases
        if alias.name != "*" and _looks_like_imported_string_constant_name(alias.name)
    ]


def _module_string_bindings(
    module_name: str | None,
    *,
    repo_root: Path,
    cache: dict[Path, dict[str, str]],
) -> dict[str, str] | None:
    """Load cached string bindings for one imported module."""
    if module_name is None:
        return None
    module_path = _module_path_from_import(module_name, repo_root)
    if module_path is None:
        return None
    if module_path not in cache:
        try:
            cache[module_path] = _collect_module_string_bindings(module_path)
        except (UnicodeDecodeError, OSError, TimeoutError):
            cache[module_path] = {}
    return cache[module_path]


def _merge_imported_string_aliases(
    bindings: dict[str, str],
    module_bindings: dict[str, str],
    aliases: list[ast.alias],
) -> None:
    """Merge imported string constants into the local binding map."""
    for alias in aliases:
        if alias.name == "*":
            continue
        resolved = module_bindings.get(alias.name)
        if resolved is not None:
            bindings[alias.asname or alias.name] = resolved


def _class_nodes(tree: ast.AST) -> list[ast.ClassDef]:
    """Return all class definitions in the tree."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _class_attribute_string_bindings(class_node: ast.ClassDef) -> dict[str, str]:
    """Collect string-valued class attribute bindings for one class."""
    bindings: dict[str, str] = {}
    for body_node in class_node.body:
        for targets, value in _iter_string_assignments(body_node):
            for target in targets:
                if isinstance(target, ast.Name):
                    bindings[target.id] = value
    return bindings


def _call_nodes(tree: ast.AST) -> list[ast.Call]:
    """Return all call nodes from the AST."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)]


def _metric_names_for_call(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> tuple[str | None, set[str]]:
    """Return direct runtime metric name or helper candidates for one call."""
    method_name = _call_method_name(node)
    if method_name in _RUNTIME_METRIC_METHODS:
        return (
            _direct_metric_name(
                node,
                string_bindings=string_bindings,
                attribute_bindings=attribute_bindings,
                metric_bindings=metric_bindings,
            ),
            set(),
        )
    collector_metric_name = _direct_collector_metric_name(
        node,
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
        metric_bindings=metric_bindings,
    )
    if collector_metric_name is not None:
        return (collector_metric_name, set())
    return (
        None,
        _helper_metric_candidates(
            node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
            call_method_name=method_name,
        ),
    )


def _direct_metric_name(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> str | None:
    """Resolve the direct runtime metric name from a runtime metrics call."""
    if node.args:
        return _resolve_metric_name_expr(
            node.args[0],
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
    for keyword in node.keywords:
        if keyword.arg != "name" or keyword.value is None:
            continue
        return _resolve_metric_name_expr(
            keyword.value,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
    return None


def _collector_base_metric_expr(node: ast.Call) -> ast.expr | None:
    func = node.func
    if (
        not isinstance(func, ast.Attribute)
        or func.attr not in _DIRECT_COLLECTOR_TERMINAL_METHODS
    ):
        return None
    if isinstance(func.value, ast.Call):
        labels_call = func.value
        labels_func = labels_call.func
        if isinstance(labels_func, ast.Attribute) and labels_func.attr == "labels":
            return labels_func.value
        return None
    return func.value


def _direct_collector_metric_name(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> str | None:
    metric_expr = _collector_base_metric_expr(node)
    if metric_expr is None:
        return None
    return _resolve_metric_name_expr(
        metric_expr,
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
        metric_bindings=metric_bindings,
    )


def _dict_literal_string_keys(node: ast.expr) -> frozenset[str] | None:
    """Return literal string keys when *node* is a dict literal."""
    if not isinstance(node, ast.Dict):
        return None
    keys: set[str] = set()
    for key_node in node.keys:
        if not isinstance(key_node, ast.Constant) or not isinstance(
            key_node.value, str
        ):
            return None
        keys.add(key_node.value)
    return frozenset(keys)


def _direct_metric_label_keys(node: ast.Call) -> frozenset[str] | None:
    """Resolve statically declared label keys from one direct metric call."""
    for keyword in node.keywords:
        if keyword.arg == "labels" and keyword.value is not None:
            return _dict_literal_string_keys(keyword.value)
    if len(node.args) >= 3:
        return _dict_literal_string_keys(node.args[2])
    return frozenset()


def _scan_direct_metric_label_shapes(
    tree: ast.AST,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> list[tuple[str, frozenset[str] | None, int]]:
    """Return direct metric label shapes resolved from literal label dictionaries."""
    shapes: list[tuple[str, frozenset[str] | None, int]] = []
    for call_node in _call_nodes(tree):
        if _call_method_name(call_node) not in _RUNTIME_METRIC_METHODS:
            continue
        metric_name = _direct_metric_name(
            call_node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
        if metric_name is None or not metric_name.startswith("bioetl_"):
            continue
        shapes.append(
            (
                metric_name,
                _direct_metric_label_keys(call_node),
                getattr(call_node, "lineno", 0),
            )
        )
    return shapes


def _record_label_contract_violations(
    *,
    label_contract_violations: list[str],
    label_contract_unresolved: list[str],
    relative_path: str,
    label_shapes: list[tuple[str, frozenset[str] | None, int]],
) -> None:
    """Compare direct emitter label keys against declared registry contracts."""
    for metric_name, emitted_labels, lineno in label_shapes:
        declared_labels = REGISTERED_PROMETHEUS_METRIC_LABELS.get(metric_name)
        if declared_labels is None:
            continue
        location = f"{relative_path}:{lineno}"
        if emitted_labels is None:
            label_contract_unresolved.append(f"{metric_name} @ {location}")
            continue
        missing = sorted(declared_labels - emitted_labels)
        extra = sorted(emitted_labels - declared_labels)
        if missing or extra:
            emitted = sorted(emitted_labels)
            declared = sorted(declared_labels)
            label_contract_violations.append(
                f"{metric_name} @ {location} missing={missing} extra={extra} "
                f"emitted={emitted} declared={declared}"
            )


def _partition_helper_metric_candidates(
    metric_names: set[str],
    *,
    helper_metric_names: set[str],
    alias_metric_names: set[str],
) -> None:
    """Partition helper candidate names into canonical and alias buckets."""
    for metric_name in metric_names:
        if metric_name.startswith("bioetl_"):
            helper_metric_names.add(metric_name)
        elif _is_metric_like_alias_name(metric_name):
            alias_metric_names.add(metric_name)


def _is_metric_like_alias_name(metric_name: str) -> bool:
    """Return True only for plausible Prometheus-style alias metric names."""
    normalized = metric_name.strip()
    if not normalized:
        return False
    if not _PROMETHEUS_METRIC_NAME_RE.fullmatch(normalized):
        return False
    if "_" not in normalized:
        return False
    if normalized.startswith(_NON_METRIC_ALIAS_PREFIXES):
        return False
    return normalized.endswith(tuple(_PROMETHEUS_ALIAS_SUFFIXES))


def _record_runtime_mentions(
    *,
    canonical_mentions: dict[str, list[str]],
    helper_backed_mentions: dict[str, list[str]],
    alias_mentions: dict[str, list[str]],
    relative_path: str,
    direct_metric_names: set[str],
    helper_metric_names: set[str],
    alias_metric_names: set[str],
) -> None:
    for metric_name in sorted(direct_metric_names):
        if metric_name.startswith("bioetl_"):
            canonical_mentions[metric_name].append(relative_path)
            continue
        if _is_metric_like_alias_name(metric_name):
            alias_mentions[metric_name].append(relative_path)
    for metric_name in sorted(helper_metric_names - direct_metric_names):
        helper_backed_mentions[metric_name].append(relative_path)
    for metric_name in sorted(alias_metric_names):
        alias_mentions[metric_name].append(relative_path)


def _scan_runtime_metric_file(
    path: Path,
    *,
    repo_root: Path,
    import_binding_cache: dict[Path, dict[str, str]],
    repo_attribute_bindings: dict[str, str] | None = None,
    preloaded_text: str | None = None,
) -> (
    tuple[
        str,
        set[str],
        set[str],
        set[str],
        list[tuple[str, frozenset[str] | None, int]],
    ]
    | None
):
    text = (
        preloaded_text
        if preloaded_text is not None
        else _read_runtime_candidate_text(path)
    )
    if text is None:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    string_bindings = _resolve_imported_string_bindings(
        tree,
        repo_root=repo_root,
        cache=import_binding_cache,
    )
    string_bindings.update(_collect_local_string_bindings(tree))
    metric_bindings = _resolve_imported_metric_bindings(tree)
    attribute_bindings = dict(repo_attribute_bindings or {})
    attribute_bindings.update(_collect_class_attribute_bindings(tree))
    direct_metric_names, helper_metric_names, alias_metric_names = (
        _scan_metric_names_in_tree(
            tree,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
    )
    label_shapes = _scan_direct_metric_label_shapes(
        tree,
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
        metric_bindings=metric_bindings,
    )
    return (
        _as_repo_relative(path, repo_root),
        direct_metric_names,
        helper_metric_names,
        alias_metric_names,
        label_shapes,
    )


def _scan_runtime_metric_calls(
    repo_root: Path,
) -> tuple[
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
    list[str],
    list[str],
]:
    canonical_mentions: dict[str, list[str]] = defaultdict(list)
    helper_backed_mentions: dict[str, list[str]] = defaultdict(list)
    alias_mentions: dict[str, list[str]] = defaultdict(list)
    label_contract_violations: list[str] = []
    label_contract_unresolved: list[str] = []
    import_binding_cache: dict[Path, dict[str, str]] = {}
    candidate_files = _collect_runtime_candidate_texts(repo_root)
    repo_attribute_bindings = _collect_repo_class_attribute_bindings(candidate_files)
    for path, preloaded_text in candidate_files:
        scan_result = _scan_runtime_metric_file(
            path,
            repo_root=repo_root,
            import_binding_cache=import_binding_cache,
            repo_attribute_bindings=repo_attribute_bindings,
            preloaded_text=preloaded_text,
        )
        if scan_result is None:
            continue
        (
            relative_path,
            direct_metric_names,
            helper_metric_names,
            alias_metric_names,
            label_shapes,
        ) = scan_result
        _record_runtime_mentions(
            canonical_mentions=canonical_mentions,
            helper_backed_mentions=helper_backed_mentions,
            alias_mentions=alias_mentions,
            relative_path=relative_path,
            direct_metric_names=direct_metric_names,
            helper_metric_names=helper_metric_names,
            alias_metric_names=alias_metric_names,
        )
        _record_label_contract_violations(
            label_contract_violations=label_contract_violations,
            label_contract_unresolved=label_contract_unresolved,
            relative_path=relative_path,
            label_shapes=label_shapes,
        )
    _record_static_runtime_emitters(repo_root, canonical_mentions)
    return (
        _normalize_mapping_lists(canonical_mentions),
        _normalize_mapping_lists(helper_backed_mentions),
        _normalize_mapping_lists(alias_mentions),
        sorted(label_contract_violations),
        sorted(label_contract_unresolved),
    )


def _record_static_runtime_emitters(
    repo_root: Path,
    canonical_mentions: dict[str, list[str]],
) -> None:
    """Record runtime emitters that use direct Prometheus collectors."""
    for metric_name, relative_paths in _STATIC_RUNTIME_EMITTERS.items():
        for relative_path in relative_paths:
            if (repo_root / relative_path).exists():
                canonical_mentions[metric_name].append(relative_path)


def _scan_registered_metric_names(repo_root: Path) -> frozenset[str]:
    metric_names: set[str] = set()
    for path in sorted((repo_root / _REGISTERED_SCAN_ROOT).glob("_metrics_defs_*.py")):
        try:
            text = path.read_text(encoding="utf-8")  # NOSONAR - path confined
        except UnicodeDecodeError:
            continue
        metric_names.update(_CANONICAL_METRIC_RE.findall(text))
    return frozenset(metric_names)


def _load_declared_metric_definitions(repo_root: Path) -> dict[str, set[str]]:
    path = repo_root / _DEFAULT_DECLARED_METRIC_DEFINITIONS
    if not path.exists():
        return {
            "recording_rule_metrics": set(),
            "policy_alias_metrics": set(),
            "declared_label_contract_metrics": set(),
        }
    try:
        import yaml
    except ImportError:
        return {
            "recording_rule_metrics": set(),
            "policy_alias_metrics": set(),
            "declared_label_contract_metrics": set(),
        }
    payload = yaml.safe_load(
        path.read_text(encoding="utf-8")
    )  # NOSONAR - path confined
    if not isinstance(payload, dict):
        return {
            "recording_rule_metrics": set(),
            "policy_alias_metrics": set(),
            "declared_label_contract_metrics": set(),
        }

    definitions: dict[str, set[str]] = {}
    for field in (
        "recording_rule_metrics",
        "policy_alias_metrics",
        "declared_label_contract_metrics",
    ):
        raw_metrics = payload.get(field, [])
        if not isinstance(raw_metrics, list):
            definitions[field] = set()
            continue
        definitions[field] = {
            value
            for value in raw_metrics
            if isinstance(value, str) and value.startswith("bioetl_")
        }
    return definitions


def _resolve_imported_metric_bindings(tree: ast.AST) -> dict[str, str]:
    bindings = dict(_EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS)
    for node in _import_from_nodes(tree):
        for alias in node.names:
            if alias.name == "*":
                continue
            metric_name = _EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS.get(alias.name)
            if metric_name is not None:
                bindings[alias.asname or alias.name] = metric_name
    return bindings
