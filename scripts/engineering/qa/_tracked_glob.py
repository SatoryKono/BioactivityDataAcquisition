"""Deterministic repository-wide tracked file discovery helper (Issue #12039).

This module provides the `tracked_files()` helper which bridges the gap between
standard Python `glob` and the Git index. It reads the current Git index with
`git ls-files` to ensure that collectors only process tracked files unless
explicitly opting-in.

Exceptions (collectors that intentionally scan untracked files):
- generate_semantic_pipeline_audit: Scans uncommitted pipeline outputs
- check_generic_field_ownership: Reads uncommitted test coverage output
- generate_dashboard_content_contract: Processes generated dashboard outputs
- run_observability_closure_campaign: Operates on freshly generated artifacts
- ... any other collector intentionally reading freshly generated inputs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.engineering.common.repo_paths import ensure_safe_cli_argv


def _get_tracked_paths(repo_root: Path) -> set[str]:
    """Retrieve the set of tracked file paths via git ls-files. Read afresh so staged changes are visible."""
    try:
        completed = subprocess.run(
            ensure_safe_cli_argv(["git", "ls-files", "-z"]),
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=False,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"FATAL: git ls-files failed in {repo_root}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    return {
        path
        for path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    }


def tracked_files(
    root: Path,
    *patterns: str,
    include_untracked: bool = False,
) -> tuple[Path, ...]:
    """Return file paths under `root` that match `patterns` and are tracked by Git.

    When `include_untracked` is True, returns all matching files (tracked and untracked).
    Reads the index on each call, including in linked worktrees. Fails closed (exits)
    if Git is unavailable or fails.

    Args:
        root: The directory to search within (must be within a git repository).
        patterns: One or more glob patterns (e.g. "*.py", "**/test_*.py").
                  If no patterns are provided, acts as `["*"]`.
        include_untracked: If True, do not filter by git tracked status.

    Returns:
        A deterministic (sorted) tuple of Path objects.
    """
    resolved_root = root.resolve()

    # We must find the repo root to use git ls-files properly.
    # Usually, we can just use REPO_ROOT from repo_paths, but for general use
    # and tests, we'll try to find the .git directory or use the provided root.
    repo_root = resolved_root
    while repo_root.parent != repo_root and not (repo_root / ".git").exists():
        repo_root = repo_root.parent
    if not (repo_root / ".git").exists():
        repo_root = (
            resolved_root  # Fallback, git command will likely fail if not a repo
        )

    tracked = _get_tracked_paths(repo_root) if not include_untracked else set()

    found_paths: set[Path] = set()
    effective_patterns = patterns if patterns else ("*",)

    for pattern in effective_patterns:
        # Use rglob if pattern starts with **/, else glob
        if pattern.startswith("**/"):
            iterator = resolved_root.rglob(pattern[3:])
        else:
            # If pattern contains ** somewhere else, glob supports it in Python 3.5+
            iterator = resolved_root.glob(pattern)

        for path in iterator:
            if not path.is_file():
                continue

            if not include_untracked:
                try:
                    rel_path = path.relative_to(repo_root).as_posix()
                except ValueError:
                    continue  # Not under repo root

                if rel_path not in tracked:
                    continue

            found_paths.add(path)

    return tuple(sorted(found_paths))
