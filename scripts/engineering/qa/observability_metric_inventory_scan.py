"""Source discovery and AST scanners for observability metric inventory."""

from __future__ import annotations
from bioetl.infrastructure.observability.metric_inventory_text import (
    _normalize_mapping_lists as _normalize_mapping_lists,
)
from bioetl.infrastructure.observability.metric_inventory_text import (
    _read_cached_text as _read_cached_text,
)
from bioetl.infrastructure.observability.metric_inventory_text import (
    _read_runtime_candidate_text as _read_runtime_candidate_text,
)
from bioetl.infrastructure.observability.metric_inventory_text import (
    _read_runtime_event_candidate_text as _read_runtime_event_candidate_text,
)
from bioetl.infrastructure.observability.metric_inventory_discovery import (
    _as_repo_relative as _as_repo_relative,
)
from bioetl.infrastructure.observability.metric_inventory_discovery import (
    _scan_canonical_metric_mentions_via_direct_reads as _scan_canonical_metric_mentions_via_direct_reads,
)


import ast
import os
import re
import subprocess
import types
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, cast

from scripts.engineering.qa.observability_metric_inventory_shared import (
    _CANONICAL_METRIC_RE,
    _DEFAULT_DECLARED_METRIC_DEFINITIONS as _DEFAULT_DECLARED_METRIC_DEFINITIONS,
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


from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _module_path_from_import as _module_path_from_import,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _collect_module_string_bindings as _collect_module_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _iter_string_assignments as _iter_string_assignments,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _resolve_imported_string_bindings as _resolve_imported_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _collect_class_attribute_bindings as _collect_class_attribute_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _collect_repo_class_attribute_bindings as _collect_repo_class_attribute_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _resolve_metric_name_expr as _resolve_metric_name_expr,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _collect_local_string_bindings as _collect_local_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _call_method_name as _call_method_name,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _helper_metric_candidates as _helper_metric_candidates,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _scan_metric_names_in_tree as _scan_metric_names_in_tree,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _import_from_nodes as _import_from_nodes,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _looks_like_imported_string_constant_name as _looks_like_imported_string_constant_name,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _imported_string_constant_aliases as _imported_string_constant_aliases,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _module_string_bindings as _module_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _merge_imported_string_aliases as _merge_imported_string_aliases,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _class_nodes as _class_nodes,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _class_attribute_string_bindings as _class_attribute_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _call_nodes as _call_nodes,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _metric_names_for_call as _metric_names_for_call,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _direct_metric_name as _direct_metric_name,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _collector_base_metric_expr as _collector_base_metric_expr,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _direct_collector_metric_name as _direct_collector_metric_name,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _dict_literal_string_keys as _dict_literal_string_keys,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _direct_metric_label_keys as _direct_metric_label_keys,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _scan_direct_metric_label_shapes as _scan_direct_metric_label_shapes,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _record_label_contract_violations as _record_label_contract_violations,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _partition_helper_metric_candidates as _partition_helper_metric_candidates,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _is_metric_like_alias_name as _is_metric_like_alias_name,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _record_runtime_mentions as _record_runtime_mentions,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _scan_runtime_metric_file as _scan_runtime_metric_file,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _scan_runtime_metric_calls as _scan_runtime_metric_calls,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _record_static_runtime_emitters as _record_static_runtime_emitters,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _scan_registered_metric_names as _scan_registered_metric_names,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _load_declared_metric_definitions as _load_declared_metric_definitions,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _resolve_imported_metric_bindings as _resolve_imported_metric_bindings,
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
                "--no-color",
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
