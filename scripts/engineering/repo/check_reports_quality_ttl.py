#!/usr/bin/env python3
"""Fail when reports/quality TTL artifacts exceed replay-safe retention windows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.ops.support.repo.cleanup_repository import (
    ReportsWorkspaceEvidence,
    collect_reports_workspace_evidence,
)


def _discover_repo_root(start: Path) -> Path:
    current = start.resolve()
    search_root = current if current.is_dir() else current.parent
    for candidate in (search_root, *search_root.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError(f"Could not locate repository root from {start}")


def collect_expired_reports_quality_ttl(repo_root: Path) -> list[ReportsWorkspaceEvidence]:
    """Return expired reports/quality surfaces governed by a replay-safe TTL."""
    return [
        row
        for row in collect_reports_workspace_evidence(repo_root)
        if row.rel_path.startswith("reports/quality/")
        and row.retention_ttl_days is not None
        and row.ttl_expired is True
    ]


def _report_expired_rows(rows: list[ReportsWorkspaceEvidence]) -> int:
    if not rows:
        sys.stdout.write("OK: reports/quality TTL guardrail passed.\n")
        return 0

    sys.stderr.write("ERROR: expired reports/quality TTL artifacts detected:\n")
    for row in rows:
        ttl = row.retention_ttl_days if row.retention_ttl_days is not None else "n/a"
        age = row.age_days if row.age_days is not None else "n/a"
        owner = row.retention_owner or "unowned"
        entry_id = row.retention_entry_id or "unknown"
        sys.stderr.write(
            f"  - {row.rel_path}: age_days={age} ttl_days={ttl} "
            f"owner={owner} entry_id={entry_id}\n"
        )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check reports/quality TTL artifacts against replay-safe cleanup policy."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root to scan. Defaults to auto-discovery from this script.",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = (
            args.repo_root.resolve()
            if args.repo_root is not None
            else _discover_repo_root(Path(__file__))
        )
        return _report_expired_rows(collect_expired_reports_quality_ttl(repo_root))
    except RuntimeError as exc:
        sys.stderr.write(f"ERROR: reports/quality TTL check failed: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
