from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.engineering.ci.report_pr_gate_timing import (
    ReportRequest,
    build_report,
    render_markdown,
)


REPOSITORY = "SatoryKono/BioactivityDataAcquisition"


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _run(run_id: int, created_at: datetime, updated_at: datetime) -> dict[str, Any]:
    return {
        "id": run_id,
        "run_number": run_id,
        "run_attempt": 1,
        "event": "pull_request",
        "head_branch": "fix/example",
        "head_sha": f"{run_id:040x}",
        "status": "completed",
        "conclusion": "success",
        "created_at": _iso(created_at),
        "updated_at": _iso(updated_at),
        "html_url": f"https://github.test/{run_id}",
    }


def _job(
    name: str,
    created_at: datetime,
    started_at: datetime,
    completed_at: datetime,
    *,
    conclusion: str = "success",
    runner_id: int = 42,
) -> dict[str, Any]:
    return {
        "id": hash((name, created_at)) % 100000,
        "name": name,
        "status": "completed",
        "conclusion": conclusion,
        "created_at": _iso(created_at),
        "started_at": _iso(started_at),
        "completed_at": _iso(completed_at),
        "labels": ["ubuntu-latest"],
        "runner_id": runner_id,
        "runner_name": "GitHub Actions 1",
        "runner_group_name": "GitHub Actions",
        "html_url": f"https://github.test/jobs/{name}",
        "steps": [],
    }


def _pr_gate_jobs(
    created_at: datetime,
    *,
    queue_seconds: int,
    quality_metrics_seconds: int,
    neo4j_seconds: int,
    architecture_seconds: int,
    docker_seconds: int,
    codeql_seconds: int,
    wall_seconds: int,
) -> list[dict[str, Any]]:
    started = created_at + timedelta(seconds=queue_seconds)
    quality_done = started + timedelta(seconds=quality_metrics_seconds)
    neo4j_done = started + timedelta(seconds=neo4j_seconds)
    arch_done = started + timedelta(seconds=architecture_seconds)
    docker_done = started + timedelta(seconds=docker_seconds)
    codeql_done = started + timedelta(seconds=codeql_seconds)
    wall_done = created_at + timedelta(seconds=wall_seconds)
    return [
        _job(
            "Classify changes (decision matrix)",
            created_at,
            started,
            started + timedelta(seconds=40),
        ),
        _job(
            "tests / quality-metrics-gate",
            created_at,
            started,
            quality_done,
        ),
        _job(
            "tests / neo4j-memory-live-audit",
            created_at,
            started,
            neo4j_done,
        ),
        _job(
            "lint-arch / Architecture (S7-crosscutting-architecture-a)",
            created_at,
            started,
            started + timedelta(seconds=90),
        ),
        _job(
            "lint-arch / checks-complete",
            created_at,
            arch_done - timedelta(seconds=5),
            arch_done,
        ),
        _job(
            "docker / docker-build",
            created_at,
            started,
            docker_done - timedelta(seconds=5),
        ),
        _job(
            "docker / docker-complete",
            created_at,
            docker_done - timedelta(seconds=4),
            docker_done,
        ),
        _job(
            "codeql / Analyze Python",
            created_at,
            started,
            codeql_done,
        ),
        _job(
            "pr-gate-complete",
            created_at,
            wall_done - timedelta(seconds=8),
            wall_done,
        ),
    ]


class FakeGitHubClient:
    def __init__(
        self,
        runs: list[dict[str, Any]],
        jobs_by_run_id: dict[int, list[dict[str, Any]]],
    ) -> None:
        self.runs = runs
        self.jobs_by_run_id = jobs_by_run_id

    def json(self, args: list[str]) -> Any:
        if args[:2] == ["repo", "view"]:
            return {"nameWithOwner": REPOSITORY}
        if args[0] != "api":
            raise AssertionError(args)

        endpoint = args[1]
        if "/actions/workflows/pr-required.yml/runs?" in endpoint:
            if "page=1" not in endpoint:
                return {"workflow_runs": []}
            return {"workflow_runs": self.runs}
        if "/actions/runs/" in endpoint and endpoint.endswith(
            "/jobs?per_page=100&page=1"
        ):
            run_id = int(endpoint.split("/actions/runs/", 1)[1].split("/", 1)[0])
            return {"jobs": self.jobs_by_run_id[run_id]}
        if "/actions/runs/" in endpoint and endpoint.endswith(
            "/jobs?per_page=100&page=2"
        ):
            return {"jobs": []}
        raise AssertionError(endpoint)


@pytest.mark.unit
def test_report_records_owner_paths_and_wall_clock(tmp_path: Path) -> None:
    created = datetime(2026, 9, 3, tzinfo=UTC)
    run = _run(33782300086, created, created + timedelta(seconds=1649))
    client = FakeGitHubClient(
        [run],
        {
            33782300086: _pr_gate_jobs(
                created,
                queue_seconds=80,
                quality_metrics_seconds=980,
                neo4j_seconds=565,
                architecture_seconds=480,
                docker_seconds=174,
                codeql_seconds=230,
                wall_seconds=1649,
            )
        },
    )

    report = build_report(
        client,
        ReportRequest(
            repo_root=tmp_path,
            repository=None,
            workflow="pr-required.yml",
            branch=None,
            event="pull_request",
            limit=20,
            run_ids=[],
            include_incomplete=False,
            wall_budget_seconds=300,
            queue_budget_seconds=20,
            tests_budget_seconds=245,
            architecture_budget_seconds=210,
            docker_budget_seconds=240,
            codeql_budget_seconds=240,
            generated_at=created,
        ),
    )

    assert report["metrics"]["pr_gate_wall_seconds"]["p95"] == 1649
    assert report["metrics"]["job_queue_seconds"]["p95"] == 80
    assert report["metrics"]["quality_metrics_gate_execution_seconds"]["p95"] == 980
    assert report["metrics"]["neo4j_memory_live_audit_execution_seconds"]["p95"] == 565
    assert report["acceptance"]["pr_gate_wall_p95_le_budget"] is False
    assert report["acceptance"]["job_queue_p95_le_budget"] is False
    assert report["acceptance"]["tests_owner_p95_le_budget"] is False
    assert report["acceptance"]["architecture_owner_p95_le_budget"] is False
    assert "pr_gate_wall_seconds" in render_markdown(report)


@pytest.mark.unit
def test_pr_gate_report_marks_acceptance_only_after_full_measured_sample(
    tmp_path: Path,
) -> None:
    base = datetime(2026, 9, 3, tzinfo=UTC)
    runs = [
        _run(
            index,
            base + timedelta(minutes=index),
            base + timedelta(minutes=index, seconds=190),
        )
        for index in range(1, 6)
    ]
    jobs_by_run_id = {
        int(run["id"]): _pr_gate_jobs(
            base + timedelta(minutes=index),
            queue_seconds=10,
            quality_metrics_seconds=90,
            neo4j_seconds=80,
            architecture_seconds=100,
            docker_seconds=110,
            codeql_seconds=120,
            wall_seconds=190,
        )
        for index, run in enumerate(runs, start=1)
    }
    client = FakeGitHubClient(runs, jobs_by_run_id)

    report = build_report(
        client,
        ReportRequest(
            repo_root=tmp_path,
            repository=None,
            workflow="pr-required.yml",
            branch=None,
            event="pull_request",
            limit=20,
            run_ids=[],
            include_incomplete=False,
            wall_budget_seconds=300,
            queue_budget_seconds=20,
            tests_budget_seconds=245,
            architecture_budget_seconds=210,
            docker_budget_seconds=240,
            codeql_budget_seconds=240,
            generated_at=base,
        ),
    )

    assert report["acceptance"]["pr_gate_wall_p95_le_budget"] is True
    assert report["acceptance"]["five_recent_pr_gate_success_runs_under_budget"] is True
    assert report["acceptance"]["job_queue_p95_le_budget"] is True
    assert report["acceptance"]["tests_owner_p95_le_budget"] is True
    assert report["acceptance"]["architecture_owner_p95_le_budget"] is True
    assert report["acceptance"]["docker_owner_p95_le_budget"] is True
    assert report["acceptance"]["codeql_p95_le_budget"] is True
