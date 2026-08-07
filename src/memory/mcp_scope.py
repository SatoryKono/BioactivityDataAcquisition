"""Deterministic, isolated storage scope for the file-backed MCP memory server."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def _confine_under_root(path: Path, *, root: Path) -> Path:
    """Resolve path and reject escapes outside root (Sonar path-taint confinement)."""
    resolved = path.expanduser().resolve(strict=False)
    root_resolved = root.expanduser().resolve(strict=False)
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"path escapes allowed root {root_resolved}: {path}") from exc
    return resolved

from memory.storage import atomic_write_bytes

_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9_.-]")


def _git_value(repo_root: Path, *args: str, fallback: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return fallback
    return result.stdout.strip() or fallback


def memory_scope_path(
    repo_root: Path,
    *,
    branch: str | None = None,
    commit: str | None = None,
) -> Path:
    """Return the worktree/branch/commit-bound MCP memory path."""
    resolved = repo_root.resolve()
    worktree_id = hashlib.sha256(str(resolved).encode()).hexdigest()[:16]
    branch_name = branch or _git_value(
        resolved, "branch", "--show-current", fallback="detached"
    )
    branch_name = _SAFE_COMPONENT.sub("-", branch_name)
    commit_sha = commit or _git_value(
        resolved, "rev-parse", "--verify", "HEAD", fallback="unknown"
    )
    return (
        resolved
        / ".cache"
        / "mcp-memory"
        / worktree_id
        / branch_name
        / commit_sha
        / "memory.json"
    )


def initialize_memory_file(target: Path, seed: Path) -> None:
    """Seed one scope exactly once under the shared storage lock."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    payload = seed.read_bytes()
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("MCP memory seed must be a JSON object")
    # Concurrent first users may both reach this call, but the storage primitive
    # serializes complete writes and every contender writes the identical seed.
    atomic_write_bytes(target, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    args = parser.parse_args(argv)
    repo_root = _confine_under_root(args.repo_root, root=Path.cwd())
    # seed must live under repo_root (no arbitrary path injection)
    seed = _confine_under_root(args.seed, root=repo_root)
    target = memory_scope_path(repo_root)
    initialize_memory_file(target, seed)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
