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
        ".cursor_tmp_gitshow_err.txt",
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
        ".pre-commit-config.yaml",
        ".secrets.baseline",
        "CHANGELOG.md",
        "LICENSE",
        "Makefile",
        "README.md",
        "TestChEMBLPipelineE2E.test_chembl_activity_full_run",
        "all_fixtures.txt",
        "assets",
        "commitlint.config.js",
        "configs",
        "coverage.json",
        "data",
        "dev_setup.sh",
        "docs",
        "git_commit_err.txt",
        "git_commit_out.txt",
        "grafana",
        "log_test.txt",
        "mkdocs.yml",
        "pyproject.toml",
        "reports",
        "requirements.txt",
        "scripts",
        "src",
        "test_backfill_clears_silver_only",
        "test_chembl_and_uniprot_sequential_run",
        "test_failed_run_preserves_partial_data",
        "test_health_check",
        "test_multiple_chembl_entities_parallel_safe",
        "test_pipeline_idempotency",
        "test_pipeline_resume_after_failure",
        "test_pubchem_compound_pipeline",
        "test_rebuild_clears_existing_data",
        "test_vacuum_respects_retention_days",
        "test_vacuum_runs_after_successful_pipeline",
        "tests",
        "unified_classification.csv",
        "unified_classification.xlsx",
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
