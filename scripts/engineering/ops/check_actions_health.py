#!/usr/bin/env python3
"""Report failed GitHub Actions jobs that never started a step."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode


def api_pages(endpoint: str) -> list[dict]:
    result = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", endpoint],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", help="UTC start date or timestamp (inclusive)")
    parser.add_argument("--until", help="UTC end date or timestamp (exclusive)")
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="owner/repository; defaults to gh repository",
    )
    args = parser.parse_args()
    now = datetime.now(UTC)
    since = args.since or (now - timedelta(hours=24)).isoformat(timespec="seconds")
    until = args.until or now.isoformat(timespec="seconds")
    try:
        start = datetime.fromisoformat(since.replace("Z", "+00:00"))
        end = datetime.fromisoformat(until.replace("Z", "+00:00"))
        start = (
            start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
        )
        end = end.replace(tzinfo=UTC) if end.tzinfo is None else end.astimezone(UTC)
        if start >= end:
            parser.error("--since must be earlier than --until")
        repo = (
            args.repo
            or subprocess.run(
                [
                    "gh",
                    "repo",
                    "view",
                    "--json",
                    "nameWithOwner",
                    "--jq",
                    ".nameWithOwner",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        created = f"{start.isoformat()}..{end.isoformat()}"
        query = urlencode({"per_page": 100, "created": created})
        pages = api_pages(f"repos/{repo}/actions/runs?{query}")
        if pages and pages[0]["total_count"] > 1000:
            raise ValueError("More than 1000 runs match; use a narrower time window")
        failed = set()
        for page in pages:
            for run in page["workflow_runs"]:
                created_at = datetime.fromisoformat(
                    run["created_at"].replace("Z", "+00:00")
                )
                if not start <= created_at < end:
                    continue
                jobs_pages = api_pages(
                    f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100&filter=all"
                )
                if any(
                    job["conclusion"] == "failure" and not job["steps"]
                    for jobs_page in jobs_pages
                    for job in jobs_page["jobs"]
                ):
                    failed.add(run["id"])
        if failed:
            print(
                "Failed runs with zero-step jobs: "
                + ", ".join(map(str, sorted(failed)))
            )
            return 1
        print(
            f"No failed zero-step jobs found between {start.isoformat()} and {end.isoformat()}."
        )
        return 0
    except (
        subprocess.CalledProcessError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        detail = (
            exc.stderr.strip()
            if isinstance(exc, subprocess.CalledProcessError) and exc.stderr
            else str(exc)
        )
        print(f"Actions health check failed: {detail}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
