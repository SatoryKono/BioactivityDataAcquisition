from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.engineering.ci.report_docker_actions_timing import (
    build_report,
    render_markdown,
)
from tests.unit.scripts.ci.timing_api_fakes import PagedAttemptClient


REPOSITORY = "SatoryKono/BioactivityDataAcquisition"


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _run(run_id: int, created_at: datetime, updated_at: datetime) -> dict[str, Any]:
    return {
        "id": run_id,
        "run_number": run_id,
        "run_attempt": 1,
        "event": "push",
        "head_branch": "main",
        "head_sha": f"{run_id:040x}",
        "status": "completed",
        "conclusion": "success",
        "created_at": _iso(created_at),
        "updated_at": _iso(updated_at),
        "html_url": f"https://github.test/{run_id}",
        "pull_requests": [
            {"base": {"sha": f"{run_id:040x}"}, "head": {"sha": f"{run_id:040x}"}}
        ],
    }


def _step(name: str, started_at: datetime, seconds: int) -> dict[str, Any]:
    return {
        "name": name,
        "status": "completed",
        "conclusion": "success",
        "started_at": _iso(started_at),
        "completed_at": _iso(started_at + timedelta(seconds=seconds)),
    }


def _job(
    name: str,
    created_at: datetime,
    started_at: datetime,
    completed_at: datetime,
    *,
    conclusion: str = "success",
    runner_id: int = 42,
    steps: list[dict[str, Any]] | None = None,
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
        "steps": steps or [],
    }


def _docker_jobs(
    created_at: datetime,
    *,
    build_queue_seconds: int,
    build_execution_seconds: int,
    owner_elapsed_seconds: int,
    publish_conclusion: str = "cancelled",
) -> list[dict[str, Any]]:
    build_started = created_at + timedelta(seconds=build_queue_seconds)
    build_completed = build_started + timedelta(seconds=build_execution_seconds)
    complete_created = build_completed
    complete_started = complete_created + timedelta(seconds=12)
    complete_completed = created_at + timedelta(seconds=owner_elapsed_seconds)
    publish_started = complete_completed + timedelta(seconds=1)
    publish_completed = publish_started + timedelta(minutes=65)
    return [
        _job(
            "docker-runtime-contracts",
            created_at,
            created_at + timedelta(seconds=2),
            created_at + timedelta(seconds=40),
        ),
        _job(
            "docker-lint",
            created_at,
            created_at + timedelta(seconds=3),
            created_at + timedelta(seconds=20),
        ),
        _job(
            "docker-compose-validate",
            created_at,
            created_at + timedelta(seconds=4),
            created_at + timedelta(seconds=30),
        ),
        _job(
            "docker-build",
            created_at,
            build_started,
            build_completed,
            steps=[
                _step("Build Docker image", build_started, 120),
                _step(
                    "Run full Trivy JSON evidence scan",
                    build_started + timedelta(seconds=130),
                    25,
                ),
                _step(
                    "Generate SBOM for the scanned local image",
                    build_started + timedelta(seconds=160),
                    8,
                ),
            ],
        ),
        _job(
            "docker-complete",
            complete_created,
            complete_started,
            complete_completed,
        ),
        _job(
            "docker-push",
            complete_completed + timedelta(seconds=1),
            publish_started,
            publish_completed,
            conclusion=publish_conclusion,
            runner_id=0,
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
        if "/actions/workflows/docker.yml/runs?" in endpoint:
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
def test_report_separates_docker_validation_path_from_publish_wait(
    tmp_path: Path,
) -> None:
    created = datetime(2026, 9, 3, tzinfo=UTC)
    run = _run(33766018515, created, created + timedelta(minutes=72))
    client = FakeGitHubClient(
        [run],
        {
            33766018515: _docker_jobs(
                created,
                build_queue_seconds=100,
                build_execution_seconds=174,
                owner_elapsed_seconds=412,
                publish_conclusion="cancelled",
            )
        },
    )

    report = build_report(
        client,
        repo_root=tmp_path,
        repository=None,
        workflow="docker.yml",
        branch="main",
        event=None,
        limit=20,
        run_ids=[],
        include_incomplete=False,
        owner_budget_seconds=240,
        queue_budget_seconds=20,
        generated_at=created,
    )

    assert report["metrics"]["docker_owner_elapsed_seconds"]["p95"] == 412
    assert report["metrics"]["docker_build_queue_seconds"]["p95"] == 100
    assert report["metrics"]["build_image_seconds"]["p95"] == 120
    assert report["acceptance"]["docker_owner_p95_le_budget"] is False
    assert report["acceptance"]["docker_build_queue_p95_le_budget"] is False
    assert report["acceptance"]["publish_digest_proof_available"] is False
    assert report["runs"][0]["docker_publish"]["conclusion"] == "cancelled"
    assert report["runs"][0]["cache_status"] == "unknown"
    assert report["runs"][0]["cache_key"] is None
    assert report["runs"][0]["cache_env"] == ["ubuntu-latest"]


@pytest.mark.unit
def test_docker_report_marks_acceptance_only_after_full_measured_sample(
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
        int(run["id"]): _docker_jobs(
            base + timedelta(minutes=index),
            build_queue_seconds=10,
            build_execution_seconds=120,
            owner_elapsed_seconds=190,
            publish_conclusion="success" if index == 5 else "skipped",
        )
        for index, run in enumerate(runs, start=1)
    }
    client = FakeGitHubClient(runs, jobs_by_run_id)

    report = build_report(
        client,
        repo_root=tmp_path,
        repository=None,
        workflow="docker.yml",
        branch="main",
        event=None,
        limit=20,
        run_ids=[],
        include_incomplete=False,
        owner_budget_seconds=240,
        queue_budget_seconds=20,
        generated_at=base,
    )

    assert report["acceptance"]["docker_owner_p95_le_budget"] is True
    assert (
        report["acceptance"]["five_recent_docker_owner_success_runs_under_budget"]
        is True
    )
    assert report["acceptance"]["docker_build_queue_p95_le_budget"] is True
    assert report["acceptance"]["publish_digest_proof_available"] is True
    assert report["acceptance"]["published_digest_run_ids"] == [5]
    assert "docker_owner_elapsed_seconds" in render_markdown(report)


@pytest.mark.unit
def test_write_text_refuses_path_escape(tmp_path: Path) -> None:
    from scripts.engineering.ci.report_docker_actions_timing import _write_text

    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.json"
    with pytest.raises(ValueError, match="refusing path"):
        _write_text(str(outside), "{}\n", root=root)


@pytest.mark.unit
def test_write_text_confines_relative_output(tmp_path: Path) -> None:
    from scripts.engineering.ci.report_docker_actions_timing import _write_text

    _write_text("out/report.json", "{}\n", root=tmp_path)
    written = tmp_path / "out" / "report.json"
    assert written.read_text(encoding="utf-8") == "{}\n"


@pytest.mark.unit
def test_docker_report_pagination_and_all_attempts(tmp_path: Path) -> None:
    base = datetime(2026, 9, 3, tzinfo=UTC)
    runs = []
    jobs_by_run_id = {}

    # 2 runs: one is attempt 2, one is attempt 1
    # Run 1: attempt 2 (latest)
    r1 = _run(1, base, base + timedelta(minutes=1))
    r1["run_attempt"] = 2
    runs.append(r1)

    # Run 2: attempt 1
    r2 = _run(2, base + timedelta(minutes=2), base + timedelta(minutes=3))
    r2["run_attempt"] = 1
    runs.append(r2)

    # Run 1, attempt 2 jobs
    jobs_by_run_id[1] = {
        2: _docker_jobs(
            base,
            build_queue_seconds=10,
            build_execution_seconds=120,
            owner_elapsed_seconds=190,
            publish_conclusion="success",
        ),
        1: _docker_jobs(
            base,
            build_queue_seconds=20,
            build_execution_seconds=120,
            owner_elapsed_seconds=200,
            publish_conclusion="skipped",
        ),
    }

    # Run 2, attempt 1 jobs
    jobs_by_run_id[2] = {
        1: _docker_jobs(
            base + timedelta(minutes=2),
            build_queue_seconds=30,
            build_execution_seconds=120,
            owner_elapsed_seconds=210,
            publish_conclusion="success",
        )
    }

    client = PagedAttemptClient(
        repository=REPOSITORY,
        workflow_token="/actions/workflows/docker.yml/runs?",
        pages={1: [runs[0]], 2: [runs[1]]},
        jobs_by_attempt=jobs_by_run_id,
    )
    report = build_report(
        client,
        repo_root=tmp_path,
        repository=None,
        workflow="docker.yml",
        branch="main",
        event=None,
        limit=20,
        run_ids=[],
        include_incomplete=False,
        owner_budget_seconds=240,
        queue_budget_seconds=20,
        generated_at=base,
    )

    observed = [
        (run["id"], run["run_attempt"], run["retries"]) for run in report["runs"]
    ]
    assert observed == [(1, 2, 1), (1, 1, 1), (2, 1, 0)]
    by_attempt = {run["run_attempt"]: run for run in report["runs"] if run["id"] == 1}
    assert by_attempt[2]["docker_build"]["queue_seconds"] == 10
    assert by_attempt[1]["docker_build"]["queue_seconds"] == 20


@pytest.mark.unit
def test_docker_report_missing_timestamps_skipped_cancelled(tmp_path: Path) -> None:
    # Also verify that queue_seconds is unknown and skipped doesn't result in 0 exec seconds.
    base = datetime(2026, 9, 3, tzinfo=UTC)
    run = _run(1, base, base)
    # Remove created_at / updated_at
    run["created_at"] = None
    run["updated_at"] = None

    jobs = _docker_jobs(
        base,
        build_queue_seconds=10,
        build_execution_seconds=120,
        owner_elapsed_seconds=190,
        publish_conclusion="success",
    )
    jobs[-1]["conclusion"] = "cancelled"
    jobs[0]["conclusion"] = "skipped"
    jobs[0]["completed_at"] = jobs[0]["started_at"]
    build = next(job for job in jobs if job["name"] == "docker-build")
    build["started_at"] = None

    class SkippedFakeGitHubClient:
        def json(self, args: list[str]) -> Any:
            if args[:2] == ["repo", "view"]:
                return {"nameWithOwner": REPOSITORY}
            endpoint = args[1]
            if "/actions/workflows/docker.yml/runs?" in endpoint:
                if "&page=1" in endpoint or endpoint.endswith("page=1"):
                    return {"workflow_runs": [run]}
                return {"workflow_runs": []}
            if "/jobs?" in endpoint:
                return {"jobs": jobs}
            return {}

    client = SkippedFakeGitHubClient()
    report = build_report(
        client,
        repo_root=tmp_path,
        repository=None,
        workflow="docker.yml",
        branch="main",
        event=None,
        limit=20,
        run_ids=[],
        include_incomplete=False,
        owner_budget_seconds=240,
        queue_budget_seconds=20,
        generated_at=base,
    )

    assert len(report["runs"]) == 1
    assert report["runs"][0]["docker_owner_elapsed_seconds"] is None
    assert report["runs"][0]["jobs"][0]["execution_seconds"] is None
    build_record = report["runs"][0]["docker_build"]
    assert build_record["queue_seconds"] == "unknown"
    assert report["metrics"]["docker_build_queue_seconds"]["n"] == 0
    assert report["runs"][0]["retries"] == 0


@pytest.mark.unit
def test_docker_report_reusable_docker_base_change(tmp_path: Path) -> None:
    base = datetime(2026, 9, 3, tzinfo=UTC)
    runs = []

    r1 = _run(1, base, base)
    r1["head_sha"] = "samehead"
    r1["pull_requests"] = [{"base": {"sha": "base1"}, "head": {"sha": "samehead"}}]

    r2 = _run(2, base, base)
    r2["head_sha"] = "samehead"
    r2["pull_requests"] = [{"base": {"sha": "base2"}, "head": {"sha": "samehead"}}]

    runs = [r1, r2]

    class BaseChangeFakeGitHubClient:
        def json(self, args: list[str]) -> Any:
            if args[:2] == ["repo", "view"]:
                return {"nameWithOwner": REPOSITORY}
            endpoint = args[1]
            if "/actions/workflows/docker.yml/runs?" in endpoint:
                if "&page=1" in endpoint or endpoint.endswith("page=1"):
                    return {"workflow_runs": runs}
                return {"workflow_runs": []}
            if "/jobs?" in endpoint:
                return {"jobs": []}
            return {}

    client = BaseChangeFakeGitHubClient()
    report = build_report(
        client,
        repo_root=tmp_path,
        repository=None,
        workflow="docker.yml",
        branch="main",
        event=None,
        limit=20,
        run_ids=[],
        include_incomplete=False,
        owner_budget_seconds=240,
        queue_budget_seconds=20,
        generated_at=base,
    )

    assert len(report["runs"]) == 2
    assert report["runs"][0]["base_sha"] == "base1"
    assert report["runs"][1]["base_sha"] == "base2"
    assert report["runs"][0]["head_sha"] == "samehead"
    assert report["runs"][1]["head_sha"] == "samehead"


@pytest.mark.unit
def test_docker_report_matches_reusable_caller_and_explicit_cache_label(
    tmp_path: Path,
) -> None:
    base = datetime(2026, 9, 3, tzinfo=UTC)
    run = _run(1, base, base + timedelta(minutes=4))
    jobs = _docker_jobs(
        base,
        build_queue_seconds=10,
        build_execution_seconds=120,
        owner_elapsed_seconds=190,
        publish_conclusion="success",
    )
    started_at = next(
        job["started_at"] for job in jobs if job["name"] == "docker-build"
    )
    for job in jobs:
        if job["name"] == "docker-build":
            job["name"] = "caller / docker-build"
            job["steps"] = [
                {
                    "name": "exact cache hit",
                    "status": "completed",
                    "conclusion": "skipped",
                    "started_at": started_at,
                    "completed_at": started_at,
                }
            ]
    client = FakeGitHubClient([run], {1: jobs})

    report = build_report(
        client,
        repo_root=tmp_path,
        repository=None,
        workflow="docker.yml",
        branch="main",
        event=None,
        limit=20,
        run_ids=[],
        include_incomplete=False,
        owner_budget_seconds=240,
        queue_budget_seconds=20,
        generated_at=base,
    )

    assert report["runs"][0]["docker_build"]["name"] == "caller / docker-build"
    assert report["runs"][0]["cache_status"] == "exact_hit"
    assert report["runs"][0]["docker_build"]["queue_seconds"] == 10
    step = report["runs"][0]["docker_build"]["steps"][0]
    assert step["duration_seconds"] is None
