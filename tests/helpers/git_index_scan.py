"""Git-index backed scan helpers for architecture tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True, slots=True)
class GitGrepMatch:
    """One line returned by ``git grep -n``."""

    path: str
    line_number: str
    text: str


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
