"""Paged GitHub Actions client for timing-report unit tests."""

from __future__ import annotations

import re
from typing import Any


class PagedAttemptClient:
    """Serve workflow pages, attempt payloads, and per-attempt job pages."""

    def __init__(
        self,
        *,
        repository: str,
        workflow_token: str,
        pages: dict[int, list[dict[str, Any]]],
        jobs_by_attempt: dict[int, dict[int, list[dict[str, Any]]]],
    ) -> None:
        self.repository = repository
        self.workflow_token = workflow_token
        self.pages = pages
        self.jobs_by_attempt = jobs_by_attempt

    def json(self, args: list[str]) -> Any:
        if args[:2] == ["repo", "view"]:
            return {"nameWithOwner": self.repository}
        if len(args) < 2 or args[0] != "api":
            raise AssertionError(args)
        endpoint = args[1]
        if self.workflow_token in endpoint and "/runs?" in endpoint:
            return {"workflow_runs": _runs_page(endpoint, self.pages)}
        jobs = _jobs_page(endpoint, self.jobs_by_attempt)
        if jobs is not None:
            return {"jobs": jobs}
        attempt_run = _attempt_run(endpoint, self.pages)
        if attempt_run is not None:
            return attempt_run
        return {}


def _runs_page(
    endpoint: str, pages: dict[int, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    match = re.search(r"[?&]page=(\d+)", endpoint)
    page = int(match.group(1)) if match else 1
    return pages.get(page, [])


def _jobs_page(
    endpoint: str,
    jobs_by_attempt: dict[int, dict[int, list[dict[str, Any]]]],
) -> list[dict[str, Any]] | None:
    match = re.search(r"/actions/runs/(\d+)/attempts/(\d+)/jobs", endpoint)
    if match is None:
        return None
    if "page=1" not in endpoint:
        return []
    run_id = int(match.group(1))
    attempt = int(match.group(2))
    return jobs_by_attempt.get(run_id, {}).get(attempt, [])


def _attempt_run(
    endpoint: str,
    pages: dict[int, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    match = re.search(r"/actions/runs/(\d+)/attempts/(\d+)$", endpoint)
    if match is None:
        return None
    run_id = int(match.group(1))
    attempt = int(match.group(2))
    for page_runs in pages.values():
        for run in page_runs:
            if run.get("id") == run_id:
                payload = dict(run)
                payload["run_attempt"] = attempt
                return payload
    return {}
