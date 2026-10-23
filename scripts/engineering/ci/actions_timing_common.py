"""Shared GitHub Actions attempt collection for timing reports.

The jobs API exposes attempt number, timestamps, and conclusions. It does not
expose BuildKit cache hit class or cache keys. Queue gaps stay ``unknown``
instead of borrowing another attempt's ``created_at``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import quote, urlencode

_UNMEASURED_CONCLUSIONS = frozenset({"skipped", "cancelled"})
ElapsedSeconds = Callable[[datetime | None, datetime | None], int | None]


class JsonGitHubClient(Protocol):
    """Read-only ``gh api`` JSON client."""

    def json(self, args: Sequence[str]) -> Any:
        """Return decoded JSON for one read-only ``gh`` invocation."""


WorkflowRunsEndpoint = Callable[..., str]


def queue_seconds(
    job: dict[str, Any],
    created_at: datetime | None,
    started_at: datetime | None,
) -> int | str:
    """Return queue seconds, or ``unknown`` when this attempt has no queue span."""

    if job.get("status") == "queued" and started_at is None:
        return "unknown"
    if created_at is None or started_at is None or started_at < created_at:
        return "unknown"
    return round((started_at - created_at).total_seconds())


def recorded_seconds(conclusion: object, elapsed: int | None) -> int | None:
    """Drop zero-length skipped or cancelled spans from measured samples."""

    if conclusion in _UNMEASURED_CONCLUSIONS and elapsed == 0:
        return None
    return elapsed


def job_timing(
    job: dict[str, Any],
    created_at: datetime | None,
    started_at: datetime | None,
    completed_at: datetime | None,
    elapsed_seconds: ElapsedSeconds,
) -> dict[str, int | str | None]:
    """Queue and execution fields shared by the timing reports."""

    execution = recorded_seconds(
        job.get("conclusion"),
        elapsed_seconds(started_at, completed_at),
    )
    return {
        "queue_seconds": queue_seconds(job, created_at, started_at),
        "execution_seconds": execution,
    }


def pull_request_shas(run: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return ``(base_sha, tested_sha)`` from the first pull request payload."""

    pull_requests = run.get("pull_requests")
    first: dict[str, Any] = {}
    if (
        isinstance(pull_requests, list)
        and pull_requests
        and isinstance(pull_requests[0], dict)
    ):
        first = pull_requests[0]
    base_sha = _sha(_mapping(first.get("base")).get("sha"))
    tested_sha = _sha(_mapping(first.get("head")).get("sha"))
    if base_sha is None:
        base_sha = _sha(run.get("base_sha"))
    if tested_sha is None:
        tested_sha = _sha(run.get("head_sha"))
    return base_sha, tested_sha


def run_context_fields(run: dict[str, Any]) -> dict[str, Any]:
    """Identity fields that must stay attached to every attempt record."""

    base_sha, tested_sha = pull_request_shas(run)
    return {
        "id": run.get("id"),
        "run_number": run.get("run_number"),
        "run_attempt": run.get("run_attempt"),
        "retries": _retries(run),
        "event": run.get("event"),
        "head_branch": run.get("head_branch"),
        "head_sha": run.get("head_sha"),
        "base_sha": base_sha,
        "tested_sha": tested_sha,
        "workflow_path": run.get("path"),
        "workflow_code_sha": run.get("head_sha"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "raw_api": run.get("raw_api"),
    }


def collect_selected_runs(
    client: JsonGitHubClient,
    repository: str,
    *,
    workflow: str,
    branch: str | None,
    event: str | None,
    limit: int,
    run_ids: Sequence[str],
    include_incomplete: bool,
    workflow_runs_endpoint: WorkflowRunsEndpoint,
) -> list[dict[str, Any]]:
    """Collect every selected attempt for explicit run ids or a workflow page."""

    if run_ids:
        return _collect_runs_by_id(
            client,
            repository,
            run_ids=run_ids,
            include_incomplete=include_incomplete,
        )
    return _collect_workflow_runs(
        client,
        repository,
        workflow=workflow,
        branch=branch,
        event=event,
        limit=limit,
        include_incomplete=include_incomplete,
        workflow_runs_endpoint=workflow_runs_endpoint,
    )


def jobs_for_run(
    client: JsonGitHubClient,
    repository: str,
    run: dict[str, Any],
) -> list[dict[str, Any]]:
    """Load jobs for the attempt recorded on ``run``."""

    raw_id = run.get("id")
    if isinstance(raw_id, bool) or not isinstance(raw_id, int):
        return []
    return collect_jobs(client, repository, raw_id, _attempt_count(run))


def collect_jobs(
    client: JsonGitHubClient,
    repository: str,
    run_id: int,
    attempt: int,
) -> list[dict[str, Any]]:
    """Read one attempt's jobs, following ``per_page=100`` pagination."""

    jobs, _observation = collect_jobs_observation(client, repository, run_id, attempt)
    return jobs


def collect_jobs_observation(
    client: JsonGitHubClient,
    repository: str,
    run_id: int,
    attempt: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Same job pages as ``collect_jobs``, plus raw pagination counts.

    ``jobs_total_count`` stays ``None`` when the API omits it. This function
    does not classify those counts as success.
    """

    jobs: list[dict[str, Any]] = []
    total_count: int | None = None
    pages = 0
    hit_page_cap = False
    for page in range(1, 101):
        payload = client.json(
            ["api", _jobs_endpoint(repository, run_id, attempt, page)]
        )
        pages += 1
        if page == 1:
            total_count = _total_count(payload)
        page_jobs = _page_jobs(payload)
        if not page_jobs:
            break
        jobs.extend(page_jobs)
        if len(page_jobs) < 100:
            break
        if page == 100:
            hit_page_cap = True
    return jobs, {
        "jobs_fetched": len(jobs),
        "jobs_total_count": total_count,
        "pages_fetched": pages,
        "hit_page_cap": hit_page_cap,
    }


def _collect_runs_by_id(
    client: JsonGitHubClient,
    repository: str,
    *,
    run_ids: Sequence[str],
    include_incomplete: bool,
) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for run_id in run_ids:
        payload = client.json(["api", _run_endpoint(repository, run_id)])
        if not isinstance(payload, dict) or not payload:
            continue
        runs.extend(
            _expand_attempts(
                client,
                repository,
                payload,
                include_incomplete=include_incomplete,
            )
        )
    return runs


def _collect_workflow_runs(
    client: JsonGitHubClient,
    repository: str,
    *,
    workflow: str,
    branch: str | None,
    event: str | None,
    limit: int,
    include_incomplete: bool,
    workflow_runs_endpoint: WorkflowRunsEndpoint,
) -> list[dict[str, Any]]:
    if limit < 1:
        return []
    runs: list[dict[str, Any]] = []
    parents = 0
    page_size = min(limit, 100)
    for page in range(1, 101):
        payload = client.json(
            [
                "api",
                workflow_runs_endpoint(
                    repository,
                    workflow,
                    branch=branch,
                    event=event,
                    page=page,
                    page_size=page_size,
                ),
            ]
        )
        page_runs = _workflow_runs(payload)
        if not page_runs:
            break
        for run in page_runs:
            if not isinstance(run, dict):
                continue
            runs.extend(
                _expand_attempts(
                    client,
                    repository,
                    run,
                    include_incomplete=include_incomplete,
                )
            )
            parents += 1
            if parents >= limit:
                return runs
    return runs


def _expand_attempts(
    client: JsonGitHubClient,
    repository: str,
    run: dict[str, Any],
    *,
    include_incomplete: bool,
) -> list[dict[str, Any]]:
    max_attempt = _attempt_count(run)
    selected: list[dict[str, Any]] = []
    for attempt in range(max_attempt, 0, -1):
        payload = _attempt_payload(client, repository, run, attempt, max_attempt)
        if payload is None or not _is_selected(
            payload, include_incomplete=include_incomplete
        ):
            continue
        selected.append(_attempt_record(payload, attempt, max_attempt))
    return selected


def _attempt_payload(
    client: JsonGitHubClient,
    repository: str,
    run: dict[str, Any],
    attempt: int,
    max_attempt: int,
) -> dict[str, Any] | None:
    if attempt == max_attempt:
        return run
    loaded = client.json(
        [
            "api",
            f"{_run_endpoint(repository, run.get('id'))}/attempts/{attempt}",
        ]
    )
    if not isinstance(loaded, dict) or not loaded:
        return None
    return loaded


def _attempt_record(
    payload: dict[str, Any],
    attempt: int,
    max_attempt: int,
) -> dict[str, Any]:
    raw_api = {key: value for key, value in payload.items() if key != "raw_api"}
    record = dict(raw_api)
    record["run_attempt"] = attempt
    record["retries"] = max_attempt - 1
    record["raw_api"] = raw_api
    return record


def _attempt_count(run: dict[str, Any]) -> int:
    raw = run.get("run_attempt", 1)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        return 1
    return raw


def _retries(run: dict[str, Any]) -> int:
    raw = run.get("retries")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return max(0, _attempt_count(run) - 1)


def _is_selected(run: dict[str, Any], *, include_incomplete: bool) -> bool:
    return include_incomplete or run.get("status") == "completed"


def _run_endpoint(repository: str, run_id: object) -> str:
    return f"repos/{repository}/actions/runs/{quote(str(run_id), safe='')}"


def _jobs_endpoint(repository: str, run_id: int, attempt: int, page: int) -> str:
    return (
        f"repos/{repository}/actions/runs/{run_id}/attempts/{attempt}/jobs?"
        f"{urlencode({'per_page': 100, 'page': page})}"
    )


def _workflow_runs(payload: object) -> list[object]:
    if not isinstance(payload, dict):
        return []
    runs = payload.get("workflow_runs", [])
    if not isinstance(runs, list):
        return []
    return runs


def _total_count(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("total_count")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _page_jobs(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        return []
    return [job for job in jobs if isinstance(job, dict)]


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _sha(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
