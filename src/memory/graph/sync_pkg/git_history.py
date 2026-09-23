"""Git history age probes extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

from memory.graph.sync_pkg._core_convert import (
    _coerce_int,
    _git_cached_commit_ages,
    _resolve_git_executable,
)

__all__ = [
    "_git_chunk_commit_ages",
    "_git_chunk_tracked_paths",
    "_git_last_commit_age_days",
    "_git_last_commit_age_days_bulk",
    "_parse_git_chunk_age_output",
    "_run_git_history_subprocess",
]


def _git_last_commit_age_days(
    root: Path,
    relative_path: str,
    today: date,
    cache: dict[str, int | None],
) -> int | None:
    if relative_path in cache:
        return cache[relative_path]
    try:
        result = _run_git_history_subprocess(
            [
                _resolve_git_executable(),
                "-C",
                str(root),
                "log",
                "-1",
                "--format=%ct",
                "--",
                relative_path,
            ],
            timeout_seconds=10.0,
        )
    except subprocess.TimeoutExpired:
        cache[relative_path] = None
        return None
    timestamp = result.stdout.strip()
    if result.returncode != 0 or not timestamp.isdigit():
        cache[relative_path] = None
        return None
    committed_at = datetime.fromtimestamp(_coerce_int(timestamp), tz=UTC).date()
    age = max(0, (today - committed_at).days)
    cache[relative_path] = age
    return age


def _git_last_commit_age_days_bulk(
    root: Path,
    relative_paths: list[str],
    today: date,
    cache: dict[str, int | None],
    *,
    chunk_size: int = 1024,
) -> dict[str, int | None]:
    unique_paths = [path for path in dict.fromkeys(relative_paths) if path]
    if not unique_paths:
        return {}

    git_executable = _resolve_git_executable()
    resolved = _git_cached_commit_ages(unique_paths, cache)
    pending_paths = [path for path in unique_paths if path not in resolved]
    for start_index in range(0, len(pending_paths), chunk_size):
        chunk = pending_paths[start_index : start_index + chunk_size]
        if not chunk:
            continue
        tracked_chunk = _git_chunk_tracked_paths(
            git_executable=git_executable,
            root=root,
            chunk=chunk,
        )
        untracked_paths = sorted(set(chunk) - set(tracked_chunk))
        for path in untracked_paths:
            cache[path] = None
            resolved[path] = None
        if not tracked_chunk:
            continue
        chunk_results = _git_chunk_commit_ages(
            git_executable=git_executable,
            root=root,
            chunk=tracked_chunk,
            today=today,
        )
        cache.update(chunk_results)
        resolved.update(chunk_results)
    return {path: resolved.get(path) for path in unique_paths}


def _run_git_history_subprocess(
    command: list[str], *, timeout_seconds: float | None = None
) -> subprocess.CompletedProcess[str]:
    """Run Git history probes with compatibility fallbacks for test doubles."""
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        raise
    except TypeError:
        # Some lightweight test doubles still implement the historical
        # positional-only signature (cmd, check, capture_output, text).
        legacy_run = cast(
            Callable[..., subprocess.CompletedProcess[str]],
            subprocess.run,
        )
        return legacy_run(command, False, True, True)


def _git_chunk_commit_ages(
    *,
    git_executable: str,
    root: Path,
    chunk: list[str],
    today: date,
) -> dict[str, int | None]:
    try:
        result = _run_git_history_subprocess(
            [
                git_executable,
                "-C",
                str(root),
                "log",
                "--format=__TS__%ct",
                "--name-only",
                "--",
                *chunk,
            ],
            timeout_seconds=10.0,
        )
    except subprocess.TimeoutExpired:
        if len(chunk) <= 1:
            return {
                path: _git_last_commit_age_days(root, path, today, {}) for path in chunk
            }
        middle = len(chunk) // 2
        first_half = _git_chunk_commit_ages(
            git_executable=git_executable,
            root=root,
            chunk=chunk[:middle],
            today=today,
        )
        second_half = _git_chunk_commit_ages(
            git_executable=git_executable,
            root=root,
            chunk=chunk[middle:],
            today=today,
        )
        first_half.update(second_half)
        return first_half
    chunk_results = dict.fromkeys(chunk)
    if result.returncode != 0:
        return chunk_results
    return _parse_git_chunk_age_output(result.stdout, chunk, today)


def _git_chunk_tracked_paths(
    *,
    git_executable: str,
    root: Path,
    chunk: list[str],
) -> list[str]:
    result = _run_git_history_subprocess(
        [
            git_executable,
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--",
            *chunk,
        ]
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _parse_git_chunk_age_output(
    output: str,
    chunk: list[str],
    today: date,
) -> dict[str, int | None]:
    chunk_results = dict.fromkeys(chunk)
    current_timestamp: int | None = None
    unresolved = set(chunk)
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("__TS__"):
            timestamp = line.removeprefix("__TS__")
            current_timestamp = _coerce_int(timestamp) if timestamp.isdigit() else None
            continue
        if current_timestamp is None or line not in unresolved:
            continue
        committed_at = datetime.fromtimestamp(current_timestamp, tz=UTC).date()
        chunk_results[line] = max(0, (today - committed_at).days)
        unresolved.remove(line)
        if not unresolved:
            break
    return chunk_results
