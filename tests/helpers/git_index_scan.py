"""Git-index backed scan helpers for architecture tests."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

_WINDOWS_GIT_FAILURE_CODES = {-1, 4294967295}


@dataclass(frozen=True, slots=True)
class GitGrepMatch:
    """One line returned by ``git grep -n``."""

    path: str
    line_number: str
    text: str


def _iter_candidate_files(
    *,
    root: Path,
    paths: tuple[str, ...],
    suffixes: tuple[str, ...],
    excluded_prefixes: tuple[str, ...] = (),
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for raw_path in paths:
        target = root / raw_path
        try:
            is_file = target.is_file()
        except OSError:
            continue
        if is_file:
            if not suffixes or target.name.endswith(suffixes):
                candidates.append(target)
            continue
        try:
            is_dir = target.is_dir()
        except OSError:
            continue
        if not is_dir:
            continue
        for current_root, dir_names, file_names in os.walk(target, topdown=True):
            current_root_path = Path(current_root)
            current_rel = current_root_path.relative_to(root).as_posix()
            dir_names[:] = [
                dir_name
                for dir_name in dir_names
                if not any(
                    f"{current_rel}/{dir_name}/".startswith(prefix)
                    for prefix in excluded_prefixes
                )
            ]
            for file_name in file_names:
                if suffixes and not file_name.endswith(suffixes):
                    continue
                path = current_root_path / file_name
                relative_path = path.relative_to(root).as_posix()
                if any(relative_path.startswith(prefix) for prefix in excluded_prefixes):
                    continue
                try:
                    if path.is_file():
                        candidates.append(path)
                except OSError:
                    continue
    return tuple(sorted(set(candidates)))


def _use_filesystem_fallback(returncode: int) -> bool:
    return returncode in _WINDOWS_GIT_FAILURE_CODES


def _filesystem_grep_fixed(
    *,
    root: Path,
    patterns: tuple[str, ...],
    paths: tuple[str, ...],
    excluded_prefixes: tuple[str, ...],
    suffixes: tuple[str, ...],
) -> tuple[GitGrepMatch, ...]:
    matches: list[GitGrepMatch] = []
    for path in _iter_candidate_files(
        root=root,
        paths=paths,
        suffixes=suffixes,
        excluded_prefixes=excluded_prefixes,
    ):
        relative_path = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, start=1):
            if any(pattern in line for pattern in patterns):
                matches.append(
                    GitGrepMatch(
                        path=relative_path,
                        line_number=str(index),
                        text=line,
                    )
                )
    return tuple(matches)


def _filesystem_tracked_files(
    *,
    root: Path,
    paths: tuple[str, ...],
    suffixes: tuple[str, ...],
) -> tuple[Path, ...]:
    return _iter_candidate_files(
        root=root,
        paths=paths,
        suffixes=suffixes,
    )


def git_grep_fixed(
    *,
    root: Path,
    patterns: tuple[str, ...],
    paths: tuple[str, ...],
    excluded_prefixes: tuple[str, ...] = (),
    suffixes: tuple[str, ...] = (),
    timeout: float = 30.0,
) -> tuple[GitGrepMatch, ...]:
    """Run bounded ``git grep -F`` over tracked files only.

    Architecture tests should prefer this over ``Path.rglob`` for repo-wide
    source scans, especially on Windows/WSL mounted worktrees.
    """
    command = ["git", "grep", "-n", "-F"]
    for pattern in patterns:
        command.extend(("-e", pattern))
    command.append("--")
    if suffixes:
        command.extend(
            f":(glob){path}/**/*{suffix}" for path in paths for suffix in suffixes
        )
    else:
        command.extend(paths)
    command.extend(f":(exclude){prefix}**" for prefix in excluded_prefixes)

    try:
        result = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            f"git grep scan timed out after {timeout:.1f}s: {command!r}"
        ) from exc
    if result.returncode == 1:
        return ()
    if _use_filesystem_fallback(result.returncode):
        return _filesystem_grep_fixed(
            root=root,
            patterns=patterns,
            paths=paths,
            excluded_prefixes=excluded_prefixes,
            suffixes=suffixes,
        )
    if result.returncode != 0:
        raise AssertionError(
            f"git grep scan failed with exit code {result.returncode}: {result.stderr}"
        )

    matches: list[GitGrepMatch] = []
    for line in result.stdout.splitlines():
        path, line_number, text = line.split(":", 2)
        matches.append(GitGrepMatch(path=path, line_number=line_number, text=text))
    return tuple(matches)


def git_tracked_files(
    *,
    root: Path,
    paths: tuple[str, ...],
    suffixes: tuple[str, ...] = (),
    timeout: float = 30.0,
) -> tuple[Path, ...]:
    """Return tracked files under ``paths`` without walking the filesystem."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", *paths],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            f"git ls-files scan timed out after {timeout:.1f}s: {paths!r}"
        ) from exc
    if _use_filesystem_fallback(result.returncode):
        return _filesystem_tracked_files(
            root=root,
            paths=paths,
            suffixes=suffixes,
        )
    if result.returncode != 0:
        raise AssertionError(
            "git ls-files scan failed with exit code "
            f"{result.returncode}: {result.stderr}"
        )
    files = tuple(
        root / rel_path
        for rel_path in result.stdout.splitlines()
        if not suffixes or rel_path.endswith(suffixes)
    )
    return files


__all__ = ["GitGrepMatch", "git_grep_fixed", "git_tracked_files"]
