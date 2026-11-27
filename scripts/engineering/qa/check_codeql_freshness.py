#!/usr/bin/env python3
"""Fail when the latest CodeQL analysis on a branch is missing or stale."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="main", help="Branch name")
    parser.add_argument("--max-age-days", type=int, default=7)
    args = parser.parse_args()
    if args.max_age_days < 0:
        parser.error("--max-age-days must be non-negative")

    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                "--method",
                "GET",
                "--paginate",
                "--slurp",
                "repos/{owner}/{repo}/code-scanning/analyses",
                "-f",
                "tool_name=CodeQL",
                "-f",
                f"ref=refs/heads/{args.ref}",
                "-f",
                "per_page=100",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        pages = json.loads(result.stdout)
        analyses = [analysis for page in pages for analysis in page]
        if not analyses:
            print(f"No CodeQL analyses found for {args.ref}", file=sys.stderr)
            return 1
        latest = max(
            analyses,
            key=lambda item: datetime.fromisoformat(
                item["created_at"].replace("Z", "+00:00")
            ),
        )
        created = datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00"))
        if created.tzinfo is None:
            raise ValueError("analysis timestamp has no timezone")
        print(
            f"Latest CodeQL analysis: id={latest['id']} created_at={latest['created_at']}"
        )
        if created > datetime.now(UTC) or datetime.now(UTC) - created > timedelta(
            days=args.max_age_days
        ):
            print("CodeQL analysis is stale or has a future timestamp", file=sys.stderr)
            return 1
        return 0
    except (
        subprocess.CalledProcessError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        detail = (
            exc.stderr.strip()
            if isinstance(exc, subprocess.CalledProcessError)
            else str(exc)
        )
        print(f"Failed to check CodeQL freshness: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
