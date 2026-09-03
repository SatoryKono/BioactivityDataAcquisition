#!/usr/bin/env python3
"""Report PR Gate Complete timing evidence from GitHub Actions.

Read-only collector for #9975/#9978: wall-clock of ``pr-gate-complete``,
queue vs execution, and Tests/Architecture/Docker/CodeQL owner paths.
Does not change repository settings, runner labels, budgets, or workflows.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlencode

REPO_ROOT = Path(__file__).resolve().parents[3]
if __package__ in {None, ""}:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.engineering.common.repo_paths import ensure_path_within_root, resolve_cli_path
from scripts.engineering.repo.github_settings_review import (
    GitHubReviewError,
    ReadOnlyGitHubClient,
)

DEFAULT_WORKFLOW = "pr-required.yml"
SCHEMA_VERSION = "pr-gate-timing-v1"
PR_GATE_JOB = "pr-gate-complete"
CLASSIFY_JOB = "Classify changes (decision matrix)"
QUALITY_METRICS_JOB = "tests / quality-metrics-gate"
NEO4J_JOB = "tests / neo4j-memory-live-audit"
ARCH_COMPLETE_JOB = "lint-arch / checks-complete"
DOCKER_COMPLETE_JOB = "docker / docker-complete"
CODEQL_JOB = "codeql / Analyze Python"


@dataclass(frozen=True)
class ReportRequest:
    repo_root: Path
    repository: str | None
    workflow: str
    branch: str | None
    event: str | None
    limit: int
    run_ids: Sequence[str]
    include_incomplete: bool
    wall_budget_seconds: int
    queue_budget_seconds: int
    tests_budget_seconds: int
    architecture_budget_seconds: int
    docker_budget_seconds: int
    codeql_budget_seconds: int
    generated_at: datetime | None = None


class JsonGitHubClient(Protocol):
    """Minimal read-only interface used by the report builder."""

    def json(self, args: Sequence[str]) -> Any:
        """Return decoded JSON from a read-only ``gh`` invocation."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Collect PR Gate Complete timing/capacity evidence for #9975/#9978."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root used for gh authentication and relative outputs.",
    )
    parser.add_argument(
        "--repository",
        help="GitHub repository in owner/name form. Defaults to gh repo view.",
    )
    parser.add_argument(
        "--workflow",
        default=DEFAULT_WORKFLOW,
        help="Workflow file name or id to inspect.",
    )
    parser.add_argument(
        "--branch",
        help="Optional head-branch filter. Omit to include every PR head.",
    )
    parser.add_argument(
        "--event",
        default="pull_request",
        help="GitHub Actions event filter. Default: pull_request.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum workflow runs to collect when --run-id is not supplied.",
    )
    parser.add_argument(
        "--run-id",
        dest="run_ids",
        action="append",
        default=[],
        help="Specific workflow run id to include. Repeatable.",
    )
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="Include queued/in-progress runs in the evidence snapshot.",
    )
    parser.add_argument(
        "--wall-budget-seconds",
        type=int,
        default=300,
        help="Full required-contour wall-clock budget in seconds.",
    )
    parser.add_argument(
        "--queue-budget-seconds",
        type=int,
        default=20,
        help="Runner queue p95 budget in seconds.",
    )
    parser.add_argument(
        "--tests-budget-seconds",
        type=int,
        default=245,
        help="Tests owner critical-path budget in seconds.",
    )
    parser.add_argument(
        "--architecture-budget-seconds",
        type=int,
        default=210,
        help="Architecture owner critical-path budget in seconds.",
    )
    parser.add_argument(
        "--docker-budget-seconds",
        type=int,
        default=240,
        help="Docker owner critical-path budget in seconds.",
    )
    parser.add_argument(
        "--codeql-budget-seconds",
        type=int,
        default=240,
        help="CodeQL owner budget in seconds.",
    )
    parser.add_argument(
        "--json-out",
        help="Write JSON evidence to this path. Defaults to stdout.",
    )
    parser.add_argument(
        "--markdown-out",
        help="Write a human-readable Markdown summary to this path.",
    )
    parser.add_argument(
        "--fail-on-acceptance-gap",
        action="store_true",
        help="Exit 1 when any acceptance flag is false.",
    )
    return parser


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw or raw.startswith("0001-"):
        return None
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    return datetime.fromisoformat(raw).astimezone(UTC)


def _elapsed_seconds(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None or end < start:
        return None
    return round((end - start).total_seconds())


def _nearest_rank(values: Sequence[int], percentile: int) -> int | None:
    ordered = sorted(values)
    if not ordered:
        return None
    index = max(0, math.ceil((percentile / 100) * len(ordered)) - 1)
    return ordered[min(index, len(ordered) - 1)]


def _stats(values: Sequence[int | None]) -> dict[str, int | None]:
    clean = sorted(value for value in values if value is not None)
    if not clean:
        return {"n": 0, "p50": None, "p95": None, "max": None}
    return {
        "n": len(clean),
        "p50": _nearest_rank(clean, 50),
        "p95": _nearest_rank(clean, 95),
        "max": clean[-1],
    }


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _repository_name(client: JsonGitHubClient, repository: str | None) -> str:
    if repository:
        return repository
    payload = client.json(["repo", "view", "--json", "nameWithOwner"])
    name = payload.get("nameWithOwner")
    if not isinstance(name, str) or "/" not in name:
        raise GitHubReviewError("could not resolve repository name")
    return name


def _workflow_runs_endpoint(
    repository: str,
    workflow: str,
    *,
    branch: str | None,
    event: str | None,
    page: int,
    page_size: int,
) -> str:
    params: dict[str, str | int] = {
        "per_page": page_size,
        "page": page,
    }
    if branch:
        params["branch"] = branch
    if event:
        params["event"] = event
    workflow_id = quote(workflow, safe="")
    return (
        f"repos/{repository}/actions/workflows/{workflow_id}/runs?{urlencode(params)}"
    )


def _run_endpoint(repository: str, run_id: str) -> str:
    return f"repos/{repository}/actions/runs/{quote(str(run_id), safe='')}"


def _jobs_endpoint(repository: str, run_id: int, page: int) -> str:
    return (
        f"repos/{repository}/actions/runs/{run_id}/jobs?"
        f"{urlencode({'per_page': 100, 'page': page})}"
    )


def _collect_runs(
    client: JsonGitHubClient,
    repository: str,
    *,
    workflow: str,
    branch: str | None,
    event: str | None,
    limit: int,
    run_ids: Sequence[str],
    include_incomplete: bool,
) -> list[dict[str, Any]]:
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
    )


def _is_selected_run(run: dict[str, Any], *, include_incomplete: bool) -> bool:
    return include_incomplete or run.get("status") == "completed"


def _collect_runs_by_id(
    client: JsonGitHubClient,
    repository: str,
    *,
    run_ids: Sequence[str],
    include_incomplete: bool,
) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for run_id in run_ids:
        run = client.json(["api", _run_endpoint(repository, run_id)])
        if _is_selected_run(run, include_incomplete=include_incomplete):
            runs.append(run)
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
) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    page_size = min(max(limit, 1), 100)
    for page in range(1, 101):
        payload = client.json(
            [
                "api",
                _workflow_runs_endpoint(
                    repository,
                    workflow,
                    branch=branch,
                    event=event,
                    page=page,
                    page_size=page_size,
                ),
            ]
        )
        page_runs = payload.get("workflow_runs", [])
        if not page_runs:
            break
        for run in page_runs:
            if _is_selected_run(run, include_incomplete=include_incomplete):
                runs.append(run)
            if len(runs) >= limit:
                return runs
    return runs


def _collect_jobs(
    client: JsonGitHubClient,
    repository: str,
    run_id: int,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for page in range(1, 101):
        payload = client.json(["api", _jobs_endpoint(repository, run_id, page)])
        page_jobs = payload.get("jobs", [])
        if not page_jobs:
            break
        jobs.extend(page_jobs)
        if len(page_jobs) < 100:
            break
    return jobs


def _job_record(job: dict[str, Any]) -> dict[str, Any]:
    created_at = _parse_timestamp(job.get("created_at"))
    started_at = _parse_timestamp(job.get("started_at"))
    completed_at = _parse_timestamp(job.get("completed_at"))
    runner_id = job.get("runner_id")
    runner_observed = isinstance(runner_id, int) and runner_id > 0
    return {
        "id": job.get("id"),
        "name": job.get("name"),
        "status": job.get("status"),
        "conclusion": job.get("conclusion"),
        "created_at": _iso(created_at),
        "started_at": _iso(started_at),
        "completed_at": _iso(completed_at),
        "queue_seconds": _elapsed_seconds(created_at, started_at),
        "execution_seconds": _elapsed_seconds(started_at, completed_at),
        "labels": job.get("labels", []),
        "runner_id": runner_id,
        "runner_name": job.get("runner_name"),
        "runner_group_name": job.get("runner_group_name"),
        "runner_observed": runner_observed,
        "html_url": job.get("html_url"),
    }


def _find_job(records: Sequence[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((record for record in records if record.get("name") == name), None)


def _jobs_with_prefix(
    records: Sequence[dict[str, Any]], prefix: str
) -> list[dict[str, Any]]:
    return [
        record for record in records if str(record.get("name") or "").startswith(prefix)
    ]


def _span_seconds(records: Sequence[dict[str, Any]]) -> int | None:
    starts = [_parse_timestamp(record.get("created_at")) for record in records]
    ends = [_parse_timestamp(record.get("completed_at")) for record in records]
    valid_starts = [value for value in starts if value is not None]
    valid_ends = [value for value in ends if value is not None]
    if not valid_starts or not valid_ends:
        return None
    return _elapsed_seconds(min(valid_starts), max(valid_ends))


def _timestamp_from_record(record: dict[str, Any], key: str) -> datetime | None:
    return _parse_timestamp(record.get(key))


def _peak_runner_jobs(job_records: Sequence[dict[str, Any]]) -> int:
    events: list[tuple[datetime, int]] = []
    for job in job_records:
        if not job.get("runner_observed"):
            continue
        started_at = _timestamp_from_record(job, "started_at")
        completed_at = _timestamp_from_record(job, "completed_at")
        if started_at is None or completed_at is None:
            continue
        events.append((started_at, 1))
        events.append((completed_at, -1))

    active = 0
    peak = 0
    for _timestamp, delta in sorted(events, key=lambda item: (item[0], -item[1])):
        active += delta
        peak = max(peak, active)
    return peak


def _summarize_run(
    run: dict[str, Any], jobs: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    run_created_at = _parse_timestamp(run.get("created_at"))
    run_updated_at = _parse_timestamp(run.get("updated_at"))
    job_records = [_job_record(job) for job in jobs]
    pr_gate = _find_job(job_records, PR_GATE_JOB)
    classify = _find_job(job_records, CLASSIFY_JOB)
    quality_metrics = _find_job(job_records, QUALITY_METRICS_JOB)
    neo4j = _find_job(job_records, NEO4J_JOB)
    arch_complete = _find_job(job_records, ARCH_COMPLETE_JOB)
    docker_complete = _find_job(job_records, DOCKER_COMPLETE_JOB)
    codeql = _find_job(job_records, CODEQL_JOB)
    tests_jobs = _jobs_with_prefix(job_records, "tests /")
    arch_jobs = _jobs_with_prefix(job_records, "lint-arch /")
    docker_jobs = _jobs_with_prefix(job_records, "docker /")
    pr_gate_completed = (
        _timestamp_from_record(pr_gate, "completed_at") if pr_gate else None
    )
    key_jobs = {
        "classify": classify,
        "pr_gate_complete": pr_gate,
        "quality_metrics_gate": quality_metrics,
        "neo4j_memory_live_audit": neo4j,
        "architecture_checks_complete": arch_complete,
        "docker_complete": docker_complete,
        "codeql": codeql,
    }
    return {
        "id": run.get("id"),
        "run_number": run.get("run_number"),
        "run_attempt": run.get("run_attempt"),
        "event": run.get("event"),
        "head_branch": run.get("head_branch"),
        "head_sha": run.get("head_sha"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "created_at": _iso(run_created_at),
        "updated_at": _iso(run_updated_at),
        "html_url": run.get("html_url"),
        "pr_gate_wall_seconds": _elapsed_seconds(run_created_at, pr_gate_completed)
        if run.get("status") == "completed"
        else None,
        "tests_owner_elapsed_seconds": _span_seconds(tests_jobs),
        "architecture_owner_elapsed_seconds": _span_seconds(arch_jobs),
        "docker_owner_elapsed_seconds": _span_seconds(docker_jobs),
        "quality_metrics_gate_execution_seconds": (
            quality_metrics.get("execution_seconds") if quality_metrics else None
        ),
        "neo4j_memory_live_audit_execution_seconds": (
            neo4j.get("execution_seconds") if neo4j else None
        ),
        "codeql_execution_seconds": codeql.get("execution_seconds") if codeql else None,
        "peak_runner_jobs": _peak_runner_jobs(job_records),
        "key_jobs": key_jobs,
        "jobs": job_records,
        "first_wave_job_count": sum(
            1 for job in job_records if _is_first_wave_queue_job(job)
        ),
        "job_count": len(job_records),
    }


def _git_head(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _metric_from_key_job(
    runs: Sequence[dict[str, Any]],
    job_key: str,
    field: str,
    *,
    runner_only: bool = False,
) -> list[int | None]:
    values: list[int | None] = []
    for run in runs:
        key_jobs = run.get("key_jobs")
        if not isinstance(key_jobs, dict):
            continue
        job = key_jobs.get(job_key)
        if not isinstance(job, dict):
            continue
        if runner_only and not job.get("runner_observed"):
            continue
        values.append(job.get(field))
    return values


def _is_first_wave_queue_job(job: dict[str, Any]) -> bool:
    """Keep runner-queue samples off aggregator jobs that wait on ``needs``."""
    if not job.get("runner_observed"):
        return False
    name = str(job.get("name") or "")
    if name == PR_GATE_JOB:
        return False
    if name.endswith(" / checks-complete") or name.endswith(" / docker-complete"):
        return False
    if "not-applicable" in name:
        return False
    return True


def _queue_values(runs: Sequence[dict[str, Any]]) -> list[int | None]:
    values: list[int | None] = []
    for run in runs:
        jobs = run.get("jobs")
        if not isinstance(jobs, list):
            continue
        for job in jobs:
            if not isinstance(job, dict) or not _is_first_wave_queue_job(job):
                continue
            values.append(job.get("queue_seconds"))
    return values


def _le_budget(value: int | None, budget: int) -> bool:
    return value is not None and value <= budget


def _acceptance(
    runs: Sequence[dict[str, Any]],
    metrics: dict[str, dict[str, int | None]],
    *,
    wall_budget_seconds: int,
    queue_budget_seconds: int,
    tests_budget_seconds: int,
    architecture_budget_seconds: int,
    docker_budget_seconds: int,
    codeql_budget_seconds: int,
) -> dict[str, Any]:
    success_runs = [
        run
        for run in runs
        if run.get("conclusion") == "success"
        and run.get("pr_gate_wall_seconds") is not None
    ]
    recent_success = sorted(
        success_runs,
        key=lambda item: str(item.get("created_at") or ""),
        reverse=True,
    )[:5]
    wall_p95 = metrics["pr_gate_wall_seconds"]["p95"]
    queue_p95 = metrics["job_queue_seconds"]["p95"]
    tests_p95 = metrics["tests_owner_elapsed_seconds"]["p95"]
    architecture_p95 = metrics["architecture_owner_elapsed_seconds"]["p95"]
    docker_p95 = metrics["docker_owner_elapsed_seconds"]["p95"]
    codeql_p95 = metrics["codeql_execution_seconds"]["p95"]
    return {
        "wall_budget_seconds": wall_budget_seconds,
        "queue_budget_seconds": queue_budget_seconds,
        "tests_budget_seconds": tests_budget_seconds,
        "architecture_budget_seconds": architecture_budget_seconds,
        "docker_budget_seconds": docker_budget_seconds,
        "codeql_budget_seconds": codeql_budget_seconds,
        "completed_run_sample_size": sum(
            1 for run in runs if run.get("status") == "completed"
        ),
        "pr_gate_success_sample_size": len(success_runs),
        "pr_gate_wall_p95_le_budget": _le_budget(wall_p95, wall_budget_seconds),
        "five_recent_pr_gate_success_runs_under_budget": bool(
            len(recent_success) == 5
            and all(
                int(run["pr_gate_wall_seconds"]) <= wall_budget_seconds
                for run in recent_success
            )
        ),
        "job_queue_p95_le_budget": _le_budget(queue_p95, queue_budget_seconds),
        "tests_owner_p95_le_budget": _le_budget(tests_p95, tests_budget_seconds),
        "architecture_owner_p95_le_budget": _le_budget(
            architecture_p95, architecture_budget_seconds
        ),
        "docker_owner_p95_le_budget": _le_budget(docker_p95, docker_budget_seconds),
        "codeql_p95_le_budget": _le_budget(codeql_p95, codeql_budget_seconds),
        "capacity_decision": (
            "NO-GO: public GitHub-hosted larger runners are unavailable on this "
            "account; self-hosted is rejected for public-fork trust. Remaining "
            "work is execution-path reduction plus measured queue evidence, not "
            "unapproved runner provisioning."
        ),
    }


def build_report(client: JsonGitHubClient, request: ReportRequest) -> dict[str, Any]:
    resolved_repository = _repository_name(client, request.repository)
    collected_runs = _collect_runs(
        client,
        resolved_repository,
        workflow=request.workflow,
        branch=request.branch,
        event=request.event,
        limit=request.limit,
        run_ids=request.run_ids,
        include_incomplete=request.include_incomplete,
    )
    summarized_runs = [
        _summarize_run(
            run,
            _collect_jobs(client, resolved_repository, int(run["id"])),
        )
        for run in collected_runs
    ]
    success_runs = [
        run for run in summarized_runs if run.get("conclusion") == "success"
    ]
    metrics: dict[str, dict[str, int | None]] = {
        "pr_gate_wall_seconds": _stats(
            [run.get("pr_gate_wall_seconds") for run in success_runs]
        ),
        "job_queue_seconds": _stats(_queue_values(summarized_runs)),
        "tests_owner_elapsed_seconds": _stats(
            [run.get("tests_owner_elapsed_seconds") for run in success_runs]
        ),
        "architecture_owner_elapsed_seconds": _stats(
            [run.get("architecture_owner_elapsed_seconds") for run in success_runs]
        ),
        "docker_owner_elapsed_seconds": _stats(
            [run.get("docker_owner_elapsed_seconds") for run in success_runs]
        ),
        "quality_metrics_gate_execution_seconds": _stats(
            _metric_from_key_job(
                summarized_runs, "quality_metrics_gate", "execution_seconds"
            )
        ),
        "neo4j_memory_live_audit_execution_seconds": _stats(
            _metric_from_key_job(
                summarized_runs, "neo4j_memory_live_audit", "execution_seconds"
            )
        ),
        "codeql_execution_seconds": _stats(
            [run.get("codeql_execution_seconds") for run in success_runs]
        ),
        "peak_runner_jobs": _stats(
            [run.get("peak_runner_jobs") for run in summarized_runs]
        ),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _iso(request.generated_at or datetime.now(UTC)),
        "repository": resolved_repository,
        "workflow": request.workflow,
        "branch": request.branch,
        "event": request.event,
        "source_git_head": _git_head(request.repo_root),
        "collection": {
            "requested_limit": request.limit,
            "run_ids": list(request.run_ids),
            "include_incomplete": request.include_incomplete,
        },
        "metrics": metrics,
        "acceptance": _acceptance(
            summarized_runs,
            metrics,
            wall_budget_seconds=request.wall_budget_seconds,
            queue_budget_seconds=request.queue_budget_seconds,
            tests_budget_seconds=request.tests_budget_seconds,
            architecture_budget_seconds=request.architecture_budget_seconds,
            docker_budget_seconds=request.docker_budget_seconds,
            codeql_budget_seconds=request.codeql_budget_seconds,
        ),
        "runs": summarized_runs,
    }


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PR Gate Complete timing evidence",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- repository: `{report['repository']}`",
        f"- workflow: `{report['workflow']}`",
        f"- event: `{report.get('event') or 'any'}`",
        f"- source_git_head: `{report.get('source_git_head') or 'unknown'}`",
        "",
        "## Summary metrics",
        "",
        "| Metric | n | p50 seconds | p95 seconds | max seconds |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, values in report["metrics"].items():
        lines.append(
            "| "
            f"`{name}` | {_fmt(values['n'])} | {_fmt(values['p50'])} | "
            f"{_fmt(values['p95'])} | {_fmt(values['max'])} |"
        )

    lines.extend(
        [
            "",
            "## Acceptance status",
            "",
            "| Check | Status |",
            "| --- | --- |",
        ]
    )
    for key, value in report["acceptance"].items():
        lines.append(f"| `{key}` | {_fmt(value)} |")

    lines.extend(
        [
            "",
            "## Runs",
            "",
            (
                "| Run | SHA | status/conclusion | wall | tests owner | "
                "architecture owner | quality-metrics | neo4j |"
            ),
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for run in report["runs"]:
        lines.append(
            "| "
            f"[{run['id']}]({run.get('html_url')}) | "
            f"`{str(run.get('head_sha') or '')[:12]}` | "
            f"{_fmt(run.get('status'))}/{_fmt(run.get('conclusion'))} | "
            f"{_fmt(run.get('pr_gate_wall_seconds'))} | "
            f"{_fmt(run.get('tests_owner_elapsed_seconds'))} | "
            f"{_fmt(run.get('architecture_owner_elapsed_seconds'))} | "
            f"{_fmt(run.get('quality_metrics_gate_execution_seconds'))} | "
            f"{_fmt(run.get('neo4j_memory_live_audit_execution_seconds'))} |"
        )
    return "\n".join(lines) + "\n"


def _write_text(raw_path: str, content: str, *, root: Path) -> None:
    safe_path = ensure_path_within_root(
        resolve_cli_path(raw_path, root=root),
        root,
    )
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(content, encoding="utf-8", newline="\n")


def _has_acceptance_gap(report: dict[str, Any]) -> bool:
    return any(value is False for value in report["acceptance"].values())


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = resolve_cli_path(args.repo_root, root=REPO_ROOT)
    client = ReadOnlyGitHubClient(repo_root)
    try:
        report = build_report(
            client,
            ReportRequest(
                repo_root=repo_root,
                repository=args.repository,
                workflow=args.workflow,
                branch=args.branch,
                event=args.event,
                limit=args.limit,
                run_ids=args.run_ids,
                include_incomplete=args.include_incomplete,
                wall_budget_seconds=args.wall_budget_seconds,
                queue_budget_seconds=args.queue_budget_seconds,
                tests_budget_seconds=args.tests_budget_seconds,
                architecture_budget_seconds=args.architecture_budget_seconds,
                docker_budget_seconds=args.docker_budget_seconds,
                codeql_budget_seconds=args.codeql_budget_seconds,
            ),
        )
    except (GitHubReviewError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json_out:
        _write_text(
            args.json_out,
            payload + "\n",
            root=repo_root,
        )
    else:
        print(payload)

    if args.markdown_out:
        _write_text(
            args.markdown_out,
            render_markdown(report),
            root=repo_root,
        )

    if args.fail_on_acceptance_gap and _has_acceptance_gap(report):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
