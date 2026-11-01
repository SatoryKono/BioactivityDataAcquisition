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

import os
import json
from fnmatch import fnmatch

import subprocess
import sys
from pathlib import Path

from scripts.engineering.common.repo_paths import ensure_safe_cli_argv


def _get_tracked_paths(repo_root: Path) -> set[str]:
    """Retrieve the set of tracked file paths via git ls-files. Read afresh so staged changes are visible."""
    receipt = repo_root / "quality-tooling-support.json"
    if not (repo_root / ".git").exists() and receipt.is_file():
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1 or not isinstance(
            payload.get("files"), dict
        ):
            raise ValueError("Invalid sdist quality-tooling support receipt")
        paths = set()
        for name, digest in payload["files"].items():
            candidate = Path(name)
            if (
                candidate.is_absolute()
                or ".." in candidate.parts
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
                or not (repo_root / candidate).is_file()
            ):
                raise ValueError(f"Invalid sdist quality-tooling support entry: {name}")
            paths.add(name)
        return paths
    try:
        completed = subprocess.run(
            ensure_safe_cli_argv(["git", "ls-files", "-z"]),
            cwd=repo_root,
            env=git_discovery_environment(),
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


def git_discovery_environment() -> dict[str, str]:
    """Bind child Git commands to the requested checkout, not inherited locations."""
    excluded = {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CEILING_DIRECTORIES",
        "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    }
    return {key: value for key, value in os.environ.items() if key not in excluded}


def _find_repo_root(root: Path) -> Path:
    return next(
        (
            p
            for p in (root, *root.parents)
            if (p / ".git").exists() or (p / "quality-tooling-support.json").is_file()
        ),
        root,
    )


def _matches_path(parts: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
    """Advance a set of path positions; ** consumes zero or more components."""
    positions = {0}
    for component in pattern:
        if component == "**":
            positions = (
                set(range(min(positions), len(parts) + 1)) if positions else set()
            )
        else:
            positions = {
                index + 1
                for index in positions
                if index < len(parts) and fnmatch(parts[index], component)
            }
    return len(parts) in positions


def _pattern_parts(pattern: str) -> tuple[str, ...]:
    if not pattern:
        raise ValueError("Unacceptable pattern: ''")
    path = Path(pattern)
    if path.is_absolute():
        raise NotImplementedError("Non-relative patterns are unsupported")
    if sys.version_info < (3, 13) and any(
        "**" in part and part != "**" for part in path.parts
    ):
        raise ValueError("Invalid pattern: '**' can only be an entire path component")
    # pathlib glob's terminal ** and trailing separator select directories only.
    if pattern.endswith(os.sep) or (
        sys.version_info < (3, 13) and path.parts and path.parts[-1] == "**"
    ):
        return ()
    return path.parts


def tracked_files(
    root: Path, *patterns: str, include_untracked: bool = False
) -> tuple[Path, ...]:
    """Match indexed paths without walking ignored trees; read the index afresh."""
    root = root.resolve()
    patterns = patterns or ("*",)
    if include_untracked:
        return tuple(
            sorted(
                {p for pattern in patterns for p in root.glob(pattern) if p.is_file()}
            )
        )
    repo_root = _find_repo_root(root)
    prefix = root.relative_to(repo_root)
    compiled = tuple(_pattern_parts(pattern) for pattern in patterns)
    found = set()
    for name in _get_tracked_paths(repo_root):
        relative = Path(name)
        if relative.is_relative_to(prefix):
            local = relative.relative_to(prefix)
            if any(_matches_path(local.parts, pattern) for pattern in compiled):
                candidate = repo_root / relative
                if candidate.is_file():
                    found.add(candidate)
    return tuple(sorted(found))
