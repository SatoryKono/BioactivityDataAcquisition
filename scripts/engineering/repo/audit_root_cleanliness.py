#!/usr/bin/env python3
"""Validate tracked repository-root files and directories."""

from __future__ import annotations

import argparse
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
        ".codex_tmp",
        ".gemini",
        ".github",
        ".jules",
        ".junie",
        ".vibe",
        ".cursor",
        ".idea",
        ".sonarlint",
        ".vscode",
        "script-codex",
        "script-gemini",
        "script-mistrall",
        "script-mistrallvibe",
        "assets",
        "configs",
        "data",
        "docs",
        "grafana",
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


def _discover_repo_root(script_root: Path) -> Path:
    """Best-effort repository root discovery that works in mixed Windows/WSL runs."""

    def _find_from(start: Path) -> Path | None:
        current = start if start.is_dir() else start.parent
        for candidate in (current, *current.parents):
            if (candidate / ".git").exists():
                return candidate
        return None

    for base in (Path.cwd(), script_root):
        resolved = _find_from(base)
        if resolved is not None:
            return resolved
    return script_root


def _run_git(repo_root: Path, *git_args: str) -> subprocess.CompletedProcess[bytes]:
    """Run git with fallbacks for path/cwd interoperability issues."""
    attempts: list[tuple[list[str], Path | None]] = [
        (["git", "-C", str(repo_root), *git_args], None),
        (["git", *git_args], repo_root),
        (["git", *git_args], Path.cwd()),
    ]
    if sys.platform == "win32":
        # Mixed WSL/Windows runs can fail to spawn native git reliably from
        # Windows Python; route through wsl as a last-resort fallback.
        attempts.extend(
            (
                (["wsl.exe", "git", *git_args], repo_root),
                (["wsl", "git", *git_args], repo_root),
            )
        )
    last_error: subprocess.CalledProcessError | None = None
    for command, cwd in attempts:
        try:
            return subprocess.run(  # nosec
                command,
                check=True,
                capture_output=True,
                text=False,
                cwd=str(cwd) if cwd is not None else None,
            )
        except subprocess.CalledProcessError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def _get_tracked_paths(repo_root: Path) -> list[str]:
    """Return tracked paths from git index, excluding staged deletions."""
    completed = _run_git(repo_root, "ls-files", "-z")
    staged_deleted = _run_git(
        repo_root,
        "diff",
        "--cached",
        "--name-only",
        "--diff-filter=D",
        "-z",
    )
    decoded = completed.stdout.decode("utf-8", errors="replace")
    deleted = {
        path
        for path in staged_deleted.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    }
    return [path for path in decoded.split("\0") if path and path not in deleted]


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


def _get_untracked_paths(repo_root: Path) -> list[str]:
    """Return untracked (non-ignored) paths from git working tree."""
    completed = _run_git(repo_root, "ls-files", "--others", "--exclude-standard", "-z")
    decoded = completed.stdout.decode("utf-8", errors="replace")
    return [path for path in decoded.split("\0") if path]


def _collect_untracked_root_files(paths: list[str]) -> set[str]:
    """Return only root-level untracked files."""
    return {path for path in paths if "/" not in path}


def _collect_untracked_root_dirs(paths: list[str]) -> set[str]:
    """Return root directory names inferred from untracked nested paths."""
    return {path.split("/", maxsplit=1)[0] for path in paths if "/" in path}


def _report_root_layout_violations(
    *,
    unexpected_root_files: list[str],
    unexpected_root_dirs: list[str],
) -> int:
    if not unexpected_root_files and not unexpected_root_dirs:
        return 0

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


def _report_missing_allowed_files(missing_allowed_files: list[str]) -> None:
    if not missing_allowed_files:
        return
    sys.stdout.write(
        "INFO: allowlisted root files currently absent (forward-compatible):\n"
    )
    for entry in missing_allowed_files:
        sys.stdout.write(f"  - {entry}\n")


def _unexpected_untracked_root_dirs(
    untracked_paths: list[str], tracked_root_dirs: set[str]
) -> list[str]:
    return sorted(
        root_dir
        for root_dir in _collect_untracked_root_dirs(untracked_paths)
        if root_dir not in tracked_root_dirs
        and root_dir not in ALLOWED_ROOT_DIRECTORIES
    )


def _report_untracked_root_entries(
    *,
    unexpected_untracked_root_files: list[str],
    unexpected_untracked_root_dirs: list[str],
) -> bool:
    has_violations = False
    if unexpected_untracked_root_files:
        has_violations = True
        sys.stdout.write(
            "WARNING: non-ignored untracked root files detected "
            "(SHOULD be moved under tests/fixtures/reports or ignored):\n"
        )
        for entry in unexpected_untracked_root_files:
            sys.stdout.write(f"  - {entry}\n")
    if unexpected_untracked_root_dirs:
        has_violations = True
        sys.stdout.write(
            "WARNING: non-ignored untracked root directories detected "
            "(SHOULD be reviewed/moved/ignored):\n"
        )
        for entry in unexpected_untracked_root_dirs:
            sys.stdout.write(f"  - {entry}\n")
    return has_violations


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate root tracked layout and flag unexpected untracked root files.",
    )
    parser.add_argument(
        "--strict-untracked",
        action="store_true",
        help="Fail when non-ignored untracked root files are present.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    script_root = Path(__file__).resolve().parents[3]
    repo_root = _discover_repo_root(script_root)

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

    root_layout_exit = _report_root_layout_violations(
        unexpected_root_files=unexpected_root_files,
        unexpected_root_dirs=unexpected_root_dirs,
    )
    if root_layout_exit:
        return root_layout_exit

    _report_missing_allowed_files(missing_allowed_files)

    try:
        untracked_paths = _get_untracked_paths(repo_root)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"ERROR: failed to query untracked paths: {exc}\n")
        return 2

    unexpected_untracked_root_files = sorted(
        _collect_untracked_root_files(untracked_paths)
    )
    unexpected_untracked_root_dirs = _unexpected_untracked_root_dirs(
        untracked_paths, tracked_root_dirs
    )
    strict_untracked_violation = _report_untracked_root_entries(
        unexpected_untracked_root_files=unexpected_untracked_root_files,
        unexpected_untracked_root_dirs=unexpected_untracked_root_dirs,
    )
    if args.strict_untracked and strict_untracked_violation:
        return 1

    sys.stdout.write(
        "OK: root layout audit passed "
        f"({len(tracked_root_files)} root files, {len(tracked_root_dirs)} root directories validated).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
