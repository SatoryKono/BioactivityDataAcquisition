#!/usr/bin/env python3
"""Report Docker workflow timing and runner-capacity evidence from GitHub Actions.

The collector is intentionally read-only: it uses the GitHub Actions runs/jobs
API through ``gh api`` and emits a machine-readable snapshot for #9977/#9978
without changing repository settings, runner labels, budgets, or workflow state.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections.abc import Sequence
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


DOCKER_BUILD_JOB = "docker-build"
DOCKER_COMPLETE_JOB = "docker-complete"
DOCKER_PUBLISH_JOB = "docker-push"
DEFAULT_WORKFLOW = "docker.yml"
SCHEMA_VERSION = "docker-actions-timing-v1"

STEP_METRIC_NAMES = {
    "Build Docker image": "build_image_seconds",
    "Capture image and runtime provenance": "runtime_provenance_seconds",
    "Prove default image health contract": "health_contract_seconds",
    "Run full Trivy JSON evidence scan": "trivy_application_scan_seconds",
    "Convert canonical Trivy JSON evidence": "trivy_sarif_convert_seconds",
    "Upload Trivy results to GitHub Security tab": "trivy_sarif_upload_seconds",
    "Generate SBOM for the scanned local image": "sbom_generation_seconds",
    "Run Trivy on pinned Wolfi runtime base image": "trivy_base_scan_seconds",
    "Export exact scanned image for publication": "image_export_seconds",
    "Transfer exact scanned image to publish job": "image_transfer_seconds",
}


class JsonGitHubClient(Protocol):
    """Minimal read-only interface used by the report builder."""

    def json(self, args: Sequence[str]) -> Any:
        """Return decoded JSON from a read-only ``gh`` invocation."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Collect Docker Actions timing/capacity evidence for #9977/#9978.")
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
        default="main",
        help="Branch filter used when --run-id is not supplied.",
    )
    parser.add_argument(
        "--event",
        help="Optional GitHub Actions event filter, for example push.",
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
        "--owner-budget-seconds",
        type=int,
        default=240,
        help="Docker validation critical-path budget in seconds.",
    )
    parser.add_argument(
        "--queue-budget-seconds",
        type=int,
        default=20,
        help="Runner queue p95 budget in seconds.",
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
    branch: str,
    event: str | None,
    page: int,
    page_size: int,
) -> str:
    params: dict[str, str | int] = {
        "branch": branch,
        "per_page": page_size,
        "page": page,
    }
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
    branch: str,
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
    branch: str,
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
    steps = [_step_record(job, step) for step in job.get("steps", [])]
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
        "steps": steps,
    }


def _step_record(job: dict[str, Any], step: dict[str, Any]) -> dict[str, Any]:
    started_at = _parse_timestamp(step.get("started_at"))
    completed_at = _parse_timestamp(step.get("completed_at"))
    return {
        "job_name": job.get("name"),
        "name": step.get("name"),
        "status": step.get("status"),
        "conclusion": step.get("conclusion"),
        "started_at": _iso(started_at),
        "completed_at": _iso(completed_at),
        "duration_seconds": _elapsed_seconds(started_at, completed_at),
    }


def _find_job(records: Sequence[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((record for record in records if record.get("name") == name), None)


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
    docker_build = _find_job(job_records, DOCKER_BUILD_JOB)
    docker_complete = _find_job(job_records, DOCKER_COMPLETE_JOB)
    docker_publish = _find_job(job_records, DOCKER_PUBLISH_JOB)
    complete_finished_at = (
        _timestamp_from_record(docker_complete, "completed_at")
        if docker_complete is not None
        else None
    )
    publish_started_at = (
        _timestamp_from_record(docker_publish, "started_at")
        if docker_publish is not None
        else None
    )
    publish_completed_at = (
        _timestamp_from_record(docker_publish, "completed_at")
        if docker_publish is not None
        else None
    )

    step_metrics: dict[str, int | None] = {}
    for step in docker_build.get("steps", []) if isinstance(docker_build, dict) else []:
        metric_name = STEP_METRIC_NAMES.get(str(step.get("name")))
        if metric_name:
            step_metrics[metric_name] = step.get("duration_seconds")

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
        "workflow_wall_seconds": _elapsed_seconds(run_created_at, run_updated_at)
        if run.get("status") == "completed"
        else None,
        "docker_owner_elapsed_seconds": _elapsed_seconds(
            run_created_at,
            complete_finished_at,
        ),
        "publish_gate_elapsed_seconds": _elapsed_seconds(
            publish_started_at,
            publish_completed_at,
        ),
        "docker_build": docker_build,
        "docker_complete": docker_complete,
        "docker_publish": docker_publish,
        "build_step_metrics": step_metrics,
        "peak_runner_jobs": _peak_runner_jobs(job_records),
        "jobs": job_records,
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


def _metric_from_job(
    runs: Sequence[dict[str, Any]],
    job_name: str,
    field: str,
    *,
    runner_only: bool = False,
) -> list[int | None]:
    values: list[int | None] = []
    for run in runs:
        job = run.get(job_name)
        if not isinstance(job, dict):
            continue
        if runner_only and not job.get("runner_observed"):
            continue
        values.append(job.get(field))
    return values


def _step_metric_values(
    runs: Sequence[dict[str, Any]],
    metric_name: str,
) -> list[int | None]:
    return [run.get("build_step_metrics", {}).get(metric_name) for run in runs]


def _acceptance(
    runs: Sequence[dict[str, Any]],
    metrics: dict[str, dict[str, int | None]],
    *,
    owner_budget_seconds: int,
    queue_budget_seconds: int,
) -> dict[str, Any]:
    owner_success_runs = [
        run
        for run in runs
        if isinstance(run.get("docker_complete"), dict)
        and run["docker_complete"].get("conclusion") == "success"
        and run.get("docker_owner_elapsed_seconds") is not None
    ]
    recent_owner_success = sorted(
        owner_success_runs,
        key=lambda item: str(item.get("created_at") or ""),
        reverse=True,
    )[:5]
    docker_owner_p95 = metrics["docker_owner_elapsed_seconds"]["p95"]
    docker_build_queue_p95 = metrics["docker_build_queue_seconds"]["p95"]
    publish_success_runs = [
        run
        for run in runs
        if isinstance(run.get("docker_publish"), dict)
        and run["docker_publish"].get("conclusion") == "success"
    ]
    return {
        "owner_budget_seconds": owner_budget_seconds,
        "queue_budget_seconds": queue_budget_seconds,
        "completed_run_sample_size": sum(
            1 for run in runs if run.get("status") == "completed"
        ),
        "docker_owner_success_sample_size": len(owner_success_runs),
        "docker_owner_p95_le_budget": bool(
            docker_owner_p95 is not None and docker_owner_p95 <= owner_budget_seconds
        ),
        "five_recent_docker_owner_success_runs_under_budget": bool(
            len(recent_owner_success) == 5
            and all(
                int(run["docker_owner_elapsed_seconds"]) <= owner_budget_seconds
                for run in recent_owner_success
            )
        ),
        "docker_build_queue_p95_le_budget": bool(
            docker_build_queue_p95 is not None
            and docker_build_queue_p95 <= queue_budget_seconds
        ),
        "publish_digest_proof_available": bool(publish_success_runs),
        "published_digest_run_ids": [run["id"] for run in publish_success_runs],
        "capacity_decision": (
            "NO-GO: collect final fan-out and queue-demand evidence before runner "
            "tier or runs-on migration."
        ),
    }


def build_report(
    client: JsonGitHubClient,
    *,
    repo_root: Path,
    repository: str | None,
    workflow: str,
    branch: str,
    event: str | None,
    limit: int,
    run_ids: Sequence[str],
    include_incomplete: bool,
    owner_budget_seconds: int,
    queue_budget_seconds: int,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    resolved_repository = _repository_name(client, repository)
    collected_runs = _collect_runs(
        client,
        resolved_repository,
        workflow=workflow,
        branch=branch,
        event=event,
        limit=limit,
        run_ids=run_ids,
        include_incomplete=include_incomplete,
    )
    summarized_runs = [
        _summarize_run(
            run,
            _collect_jobs(client, resolved_repository, int(run["id"])),
        )
        for run in collected_runs
    ]
    completed_owner_runs = [
        run
        for run in summarized_runs
        if isinstance(run.get("docker_complete"), dict)
        and run["docker_complete"].get("conclusion") == "success"
    ]
    metrics: dict[str, dict[str, int | None]] = {
        "workflow_wall_seconds": _stats(
            [run.get("workflow_wall_seconds") for run in summarized_runs]
        ),
        "docker_owner_elapsed_seconds": _stats(
            [run.get("docker_owner_elapsed_seconds") for run in completed_owner_runs]
        ),
        "docker_build_queue_seconds": _stats(
            _metric_from_job(
                summarized_runs,
                "docker_build",
                "queue_seconds",
                runner_only=True,
            )
        ),
        "docker_build_execution_seconds": _stats(
            _metric_from_job(
                summarized_runs,
                "docker_build",
                "execution_seconds",
                runner_only=True,
            )
        ),
        "docker_complete_queue_seconds": _stats(
            _metric_from_job(
                summarized_runs,
                "docker_complete",
                "queue_seconds",
                runner_only=True,
            )
        ),
        "publish_gate_elapsed_seconds": _stats(
            [run.get("publish_gate_elapsed_seconds") for run in summarized_runs]
        ),
        "peak_runner_jobs": _stats(
            [run.get("peak_runner_jobs") for run in summarized_runs]
        ),
    }
    for metric_name in STEP_METRIC_NAMES.values():
        metrics[metric_name] = _stats(_step_metric_values(summarized_runs, metric_name))

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _iso(generated_at or datetime.now(UTC)),
        "repository": resolved_repository,
        "workflow": workflow,
        "branch": branch,
        "event": event,
        "source_git_head": _git_head(repo_root),
        "collection": {
            "requested_limit": limit,
            "run_ids": list(run_ids),
            "include_incomplete": include_incomplete,
        },
        "cache_evidence": {
            "workflow_cache_from": "type=gha",
            "workflow_cache_to_policy": "main push only: type=gha,mode=max",
            "build_action_outputs": ["imageid", "digest", "metadata"],
            "note": (
                "BuildKit cache-hit detail is exposed through Docker build "
                "summary/build records and step logs; this snapshot keeps the "
                "API-level timing evidence separate from log-derived analysis."
            ),
        },
        "metrics": metrics,
        "acceptance": _acceptance(
            summarized_runs,
            metrics,
            owner_budget_seconds=owner_budget_seconds,
            queue_budget_seconds=queue_budget_seconds,
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
        "# Docker Actions timing evidence",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- repository: `{report['repository']}`",
        f"- workflow: `{report['workflow']}`",
        f"- branch: `{report['branch']}`",
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
                "| Run | SHA | status/conclusion | Docker owner seconds | "
                "Docker build queue | Docker build execution | publish proof |"
            ),
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for run in report["runs"]:
        build = (
            run.get("docker_build") if isinstance(run.get("docker_build"), dict) else {}
        )
        publish = (
            run.get("docker_publish")
            if isinstance(run.get("docker_publish"), dict)
            else {}
        )
        publish_status = publish.get("conclusion") or publish.get("status") or "absent"
        lines.append(
            "| "
            f"[{run['id']}]({run.get('html_url')}) | "
            f"`{str(run.get('head_sha') or '')[:12]}` | "
            f"{_fmt(run.get('status'))}/{_fmt(run.get('conclusion'))} | "
            f"{_fmt(run.get('docker_owner_elapsed_seconds'))} | "
            f"{_fmt(build.get('queue_seconds'))} | "
            f"{_fmt(build.get('execution_seconds'))} | "
            f"{_fmt(publish_status)} |"
        )
    return "\n".join(lines) + "\n"


def _prepare_output_path(raw_path: str, *, root: Path) -> Path:
    return ensure_path_within_root(resolve_cli_path(raw_path, root=root), root)


def _has_acceptance_gap(report: dict[str, Any]) -> bool:
    return any(value is False for value in report["acceptance"].values())


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = resolve_cli_path(args.repo_root, root=REPO_ROOT)
    client = ReadOnlyGitHubClient(repo_root)
    try:
        report = build_report(
            client,
            repo_root=repo_root,
            repository=args.repository,
            workflow=args.workflow,
            branch=args.branch,
            event=args.event,
            limit=args.limit,
            run_ids=args.run_ids,
            include_incomplete=args.include_incomplete,
            owner_budget_seconds=args.owner_budget_seconds,
            queue_budget_seconds=args.queue_budget_seconds,
        )
    except (GitHubReviewError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json_out:
        json_out = _prepare_output_path(args.json_out, root=repo_root)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(  # NOSONAR - path confined by _prepare_output_path
            payload + "\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        print(payload)

    if args.markdown_out:
        markdown_out = _prepare_output_path(args.markdown_out, root=repo_root)
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(  # NOSONAR - path confined by _prepare_output_path
            render_markdown(report),
            encoding="utf-8",
            newline="\n",
        )

    if args.fail_on_acceptance_gap and _has_acceptance_gap(report):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
