#!/usr/bin/env python3
"""Live Neo4j audit gate for deterministic memory sync."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.memory.sync import (
    DEFAULT_BATCH_SIZE,
    build_audit_report,
    build_snapshot,
    snapshot_invariant_issues,
    sync_snapshot,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply deterministic Neo4j memory sync and fail on live drift.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_ROOT,
        help="Project root directory.",
    )
    parser.add_argument(
        "--http-uri",
        type=str,
        help="Explicit Neo4j HTTP endpoint, e.g. http://localhost:7474.",
    )
    parser.add_argument(
        "--verified-at",
        type=str,
        default="2026-04-09",
        help="Stable verification date for deterministic snapshots in CI.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Maximum statements per Neo4j commit request.",
    )
    return parser


def _audit_issues(report: dict[str, object]) -> list[str]:
    live = report.get("live", {})
    if not isinstance(live, dict):
        return ["live report payload is malformed"]
    issues: list[str] = []
    issues.extend(_live_payload_issues(live))
    issues.extend(_diff_payload_issues(report.get("diff", {})))
    return issues


def _live_payload_issues(live: dict[str, object]) -> list[str]:
    """Return issues derived from live graph audit payload."""
    issues: list[str] = []
    if int(live.get("unmanaged_repo_node_total", 0)) > 0:
        issues.append("live graph contains unmanaged repo-derived nodes")
    orphan_summary = live.get("orphan_summary", {})
    if isinstance(orphan_summary, dict) and int(orphan_summary.get("total", 0)) > 0:
        issues.append("live graph contains managed orphan nodes")
    return issues


def _has_non_zero_delta(entries: object) -> bool:
    """Return True when diff payload contains a non-zero delta entry."""
    return isinstance(entries, list) and any(
        int(entry.get("delta", 0)) != 0 for entry in entries if isinstance(entry, dict)
    )


def _diff_payload_issues(diff: object) -> list[str]:
    """Return issues derived from diff section of live audit report."""
    if not isinstance(diff, dict):
        return []
    issues: list[str] = []
    if _has_non_zero_delta(diff.get("labels", [])):
        issues.append("label counts differ between snapshot and live managed graph")
    if _has_non_zero_delta(diff.get("relation_types", [])):
        issues.append("relation counts differ between snapshot and live managed graph")
    return issues


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    snapshot = build_snapshot(root, verified_at=args.verified_at)
    issues = snapshot_invariant_issues(snapshot)
    if issues:
        print(json.dumps({"snapshot": snapshot.stats(), "issues": issues}, indent=2))
        return 1

    sync_snapshot(
        snapshot,
        root,
        args.http_uri,
        batch_size=args.batch_size,
        full_reset_managed_wave=True,
        prune_legacy_unmanaged=True,
    )
    report = build_audit_report(snapshot, root, args.http_uri)
    issues = _audit_issues(report)
    print(json.dumps({"report": report, "issues": issues}, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
