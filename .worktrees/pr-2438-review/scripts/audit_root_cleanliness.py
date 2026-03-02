#!/usr/bin/env python3
"""Validate allowed files/directories in repository root."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from pathlib import Path

# Repository-root entries allowed in Git index.
ALLOWED_ROOT_ENTRIES: frozenset[str] = frozenset(
    {
        ".ai",
        ".aiassistant",
        ".claude",
        ".codex",
        ".dockerignore",
        ".setup_wsl_codex.sh",
        ".editorconfig",
        ".env.example",
        ".gemini",
        ".gitattributes",
        ".github",
        ".gitignore",
        ".gitleaks.toml",
        ".importlinter",
        ".jscpd.json",
        ".jules",
        ".junie",
        ".pre-commit-config.yaml",
        ".secrets.baseline",
        "AGENTS.md",
        "CHANGELOG.md",
        "Dockerfile",
        "LICENSE",
        "Makefile",
        "README.md",
        "assets",
        "commitlint.config.js",
        "configs",
        "data",
        "docker-compose.monitoring.yml",
        "docker-compose.yml",
        "docs",
        "entrypoint.sh",
        "grafana",
        "mkdocs.yml",
        "prompts",
        "pyproject.toml",
        "reports",
        "requirements.txt",
        "scripts",
        "src",
        "tests",
        "uv.lock",
    }
)


def _get_tracked_root_entries(repo_root: Path) -> set[str]:
    """Return all unique top-level entries from git index."""
    completed = subprocess.run(  # nosec
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=False,
    )

    entries: set[str] = set()
    for raw_path in completed.stdout.decode("utf-8", errors="replace").split("\0"):
        if not raw_path:
            continue
        entries.add(raw_path.split("/", maxsplit=1)[0])
    return entries


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    try:
        tracked_root_entries = _get_tracked_root_entries(repo_root)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"❌ Failed to query git index: {exc}\n")
        return 2

    unexpected_entries = sorted(tracked_root_entries - ALLOWED_ROOT_ENTRIES)
    missing_allowed_entries = sorted(ALLOWED_ROOT_ENTRIES - tracked_root_entries)

    if unexpected_entries:
        sys.stderr.write(
            "❌ Root layout policy violation: unexpected top-level entries found:\n"
        )
        for entry in unexpected_entries:
            sys.stderr.write(f"  - {entry}\n")
        sys.stderr.write(
            "\nMove runtime artifacts to reports/, documentation/reference files to docs/, "
            "and automation helpers to scripts/.\n"
        )
        return 1

    if missing_allowed_entries:
        sys.stdout.write(
            "ℹ️  Allowed entries not currently present (policy remains forward-compatible):\n"
        )
        for entry in missing_allowed_entries:
            sys.stdout.write(f"  - {entry}\n")

    sys.stdout.write(
        f"✅ Root layout audit passed ({len(tracked_root_entries)} tracked root entries validated).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
