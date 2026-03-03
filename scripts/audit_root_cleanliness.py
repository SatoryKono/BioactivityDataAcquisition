#!/usr/bin/env python3
"""Validate tracked repository-root files and directories."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from pathlib import Path

ALLOWLIST_FILE = Path(".github/root-allowlist.txt")

ALLOWED_ROOT_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".ai",
        ".aiassistant",
        ".claude",
        ".codex",
        ".gemini",
        ".github",
        ".jules",
        ".junie",
        "assets",
        "configs",
        "data",
        "docs",
        "grafana",
        "prompts",
        "reports",
        "scripts",
        "src",
        "tests",
    }
)


def _load_allowed_root_files(repo_root: Path) -> frozenset[str]:
    """Load canonical root-file allowlist from .github/root-allowlist.txt."""
    allowlist_path = repo_root / ALLOWLIST_FILE
    if not allowlist_path.exists():
        raise RuntimeError(f"Allowlist file does not exist: {allowlist_path}")

    entries: set[str] = set()
    with allowlist_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            cleaned = line.strip()
            if not cleaned or cleaned.startswith("#"):
                continue
            if "/" in cleaned:
                raise RuntimeError(
                    "Root allowlist must contain only root-level file names "
                    f"(invalid entry: {cleaned})"
                )
            entries.add(cleaned)

    if not entries:
        raise RuntimeError(f"Allowlist is empty: {allowlist_path}")
    return frozenset(entries)


def _get_tracked_paths(repo_root: Path) -> list[str]:
    """Return all tracked paths from git index."""
    completed = subprocess.run(  # nosec
        ["git", "-C", str(repo_root), "ls-files", "-z"],
        check=True,
        capture_output=True,
        text=False,
    )
    decoded = completed.stdout.decode("utf-8", errors="replace")
    return [path for path in decoded.split("\0") if path]


def _collect_tracked_root_entries(paths: list[str]) -> tuple[set[str], set[str]]:
    """Split tracked paths into root files and root directories."""
    root_files: set[str] = set()
    root_dirs: set[str] = set()
    for path in paths:
        if "/" not in path:
            root_files.add(path)
            continue
        root_dirs.add(path.split("/", maxsplit=1)[0])
    return root_files, root_dirs


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    try:
        allowed_root_files = _load_allowed_root_files(repo_root)
    except (OSError, RuntimeError) as exc:
        sys.stderr.write(f"ERROR: failed to load root allowlist: {exc}\n")
        return 2

    try:
        tracked_paths = _get_tracked_paths(repo_root)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"ERROR: failed to query git index: {exc}\n")
        return 2

    tracked_root_files, tracked_root_dirs = _collect_tracked_root_entries(tracked_paths)

    unexpected_root_files = sorted(tracked_root_files - allowed_root_files)
    unexpected_root_dirs = sorted(tracked_root_dirs - ALLOWED_ROOT_DIRECTORIES)
    missing_allowed_files = sorted(allowed_root_files - tracked_root_files)

    if unexpected_root_files or unexpected_root_dirs:
        sys.stderr.write("ERROR: root layout policy violation detected.\n")
        if unexpected_root_files:
            sys.stderr.write("Unexpected tracked root files:\n")
            for entry in unexpected_root_files:
                sys.stderr.write(f"  - {entry}\n")
        if unexpected_root_dirs:
            sys.stderr.write("Unexpected tracked root directories:\n")
            for entry in unexpected_root_dirs:
                sys.stderr.write(f"  - {entry}\n")
        return 1

    if missing_allowed_files:
        sys.stdout.write(
            "INFO: allowlisted root files currently absent (forward-compatible):\n"
        )
        for entry in missing_allowed_files:
            sys.stdout.write(f"  - {entry}\n")

    sys.stdout.write(
        "OK: root layout audit passed "
        f"({len(tracked_root_files)} root files, {len(tracked_root_dirs)} root directories validated).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
