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


def parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (
        result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)
    )


def is_failed_job(
    job: dict, created_at: datetime, start: datetime, end: datetime
) -> bool:
    if job["conclusion"] != "failure" or job["steps"]:
        return False
    completed_at = job.get("completed_at")
    return created_at >= start or bool(
        completed_at and start <= parse_time(completed_at) < end
    )


def failed_runs(
    repo: str, start: datetime, end: datetime, scan_start: datetime
) -> set[int]:
    query = urlencode(
        {"per_page": 100, "created": f"{scan_start.isoformat()}..{end.isoformat()}"}
    )
    pages = api_pages(f"repos/{repo}/actions/runs?{query}")
    if pages and pages[0]["total_count"] > 1000:
        raise ValueError("More than 1000 runs match; use a narrower time window")
    failed = set()
    for page in pages:
        for run in page["workflow_runs"]:
            created_at = parse_time(run["created_at"])
            if not scan_start <= created_at < end:
                continue
            jobs_pages = api_pages(
                f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100&filter=latest"
            )
            if any(
                is_failed_job(job, created_at, start, end)
                for jobs_page in jobs_pages
                for job in jobs_page["jobs"]
            ):
                failed.add(run["id"])
    return failed


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
        start = parse_time(since)
        end = parse_time(until)
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
        # Daily scans overlap by a day so jobs still queued at the previous
        # scan can be observed after they finish. Explicit ranges remain exact.
        scan_start = start - timedelta(hours=24) if args.since is None else start
        failed = failed_runs(repo, start, end, scan_start)
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
