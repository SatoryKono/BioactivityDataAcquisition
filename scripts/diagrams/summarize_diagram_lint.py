#!/usr/bin/env python3
"""Summarize diagram lint JSON report by severity and rule."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

NONE_MESSAGE = "  - none"


def _out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _err(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize output produced by scripts/diagrams/lint_diagrams.py --json",
    )
    parser.add_argument("report", type=Path, help="Path to lint JSON report")
    parser.add_argument(
        "--top-rules",
        type=int,
        default=15,
        help="How many most frequent rules to print (default: 15)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.report.exists():
        _err(f"[ERROR] Report not found: {args.report}")
        return 2

    try:
        payload = json.loads(args.report.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _err(f"[ERROR] Invalid JSON report: {exc}")
        return 2

    issues = payload.get("issues", [])
    if not isinstance(issues, list):
        _err("[ERROR] Invalid report shape: 'issues' must be a list")
        return 2

    severity_counts = Counter()
    rule_counts = Counter()
    file_counts = Counter()
    for issue in issues:
        severity = str(issue.get("severity", "UNKNOWN"))
        rule = str(issue.get("rule", "UNKNOWN"))
        file_name = str(issue.get("file", "UNKNOWN"))
        severity_counts[severity] += 1
        rule_counts[rule] += 1
        file_counts[file_name] += 1

    _out("Diagram lint summary")
    _out("====================")
    _out(f"Files checked: {payload.get('files_checked', 'n/a')}")
    _out(f"Files passed:  {payload.get('files_passed', 'n/a')}")
    _out(f"Files failed:  {payload.get('files_failed', 'n/a')}")
    _out(f"Has errors:    {payload.get('has_errors', 'n/a')}")
    _out("")

    _out("By severity:")
    for sev in sorted(severity_counts):
        _out(f"  - {sev}: {severity_counts[sev]}")
    if not severity_counts:
        _out(NONE_MESSAGE)
    _out("")

    _out(f"Top {args.top_rules} rules:")
    for rule, count in rule_counts.most_common(args.top_rules):
        _out(f"  - {rule}: {count}")
    if not rule_counts:
        _out(NONE_MESSAGE)
    _out("")

    _out("Top files by issue count:")
    for file_name, count in file_counts.most_common(10):
        _out(f"  - {file_name}: {count}")
    if not file_counts:
        _out(NONE_MESSAGE)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
