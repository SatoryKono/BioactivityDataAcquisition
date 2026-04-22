from __future__ import annotations

import json
from pathlib import Path

from scripts.engineering.qa import test_health


def test_aggregate_junit_counts_failures_errors_and_skips(tmp_path: Path) -> None:
    junit = tmp_path / "lane.xml"
    junit.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="4" failures="1" errors="1" skipped="1">
  <testcase classname="tests.unit.test_sample" name="test_pass" file="tests/unit/test_sample.py" />
  <testcase classname="tests.unit.test_sample" name="test_fail" file="tests/unit/test_sample.py">
    <failure message="AssertionError: bad value">trace</failure>
  </testcase>
  <testcase classname="tests.unit.test_sample" name="test_error" file="tests/unit/test_sample.py">
    <error message="fixture failed">trace</error>
  </testcase>
  <testcase classname="tests.unit.test_sample" name="test_skip" file="tests/unit/test_sample.py">
    <skipped message="skip reason" />
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )

    payload = test_health.aggregate_junit(
        xml_paths=[junit],
        run_id="run-1",
        suite="unit-fast",
        shards=[],
        started_at="2026-04-22T00:00:00+00:00",
        duration_seconds=1.2345,
        command=["pytest"],
        exit_code=1,
    )

    assert payload["counts"] == {
        "collected": 4,
        "passed": 1,
        "failed": 1,
        "errors": 1,
        "skipped": 1,
        "xfailed": 0,
        "xpassed": 0,
    }
    assert [failure["phase"] for failure in payload["failures"]] == [
        "failure",
        "error",
    ]
    assert [case["status"] for case in payload["cases"]] == [
        "passed",
        "failed",
        "error",
        "skipped",
    ]
    assert payload["failures"][0]["classification"] == "assertion"
    assert payload["failures"][0]["nodeid"] == ("tests/unit/test_sample.py::test_fail")


def test_classify_failure_uses_conservative_heuristics() -> None:
    assert (
        test_health.classify_failure(
            phase="error",
            file="tests/integration/adapters/test_pubmed.py",
            message="VCR cassette is missing for network replay",
        )
        == "vcr_error"
    )
    assert (
        test_health.classify_failure(
            phase="failure",
            file="tests/contract/test_snapshot.py",
            message="Snapshot assertion failed",
        )
        == "snapshot_drift"
    )
    assert (
        test_health.classify_failure(
            phase="error",
            file="tests/unit/test_env.py",
            message="Docker service unavailable",
        )
        == "environment"
    )


def test_default_classifier_config_contains_current_categories() -> None:
    classifiers, default_error, default_failure, default_unknown = (
        test_health._load_failure_classifiers()
    )

    assert [category for category, _pattern in classifiers] == [
        "timeout",
        "vcr_error",
        "snapshot_drift",
        "environment",
        "collection",
        "setup_error",
        "assertion",
    ]
    assert default_error == "setup_error"
    assert default_failure == "assertion"
    assert default_unknown == "unknown"


def test_classify_failure_can_use_custom_classifier_config(tmp_path: Path) -> None:
    config = tmp_path / "classifiers.yaml"
    config.write_text(
        """
schema_version: 1
default_error_classification: custom_setup
default_failure_classification: custom_assertion
default_unknown_classification: custom_unknown
classifiers:
  - category: service_outage
    pattern: "\\\\bservice unavailable\\\\b"
""".lstrip(),
        encoding="utf-8",
    )

    assert (
        test_health.classify_failure(
            phase="failure",
            file="tests/unit/test_service.py",
            message="Service unavailable while checking probe",
            classifier_config_path=config,
        )
        == "service_outage"
    )
    assert (
        test_health.classify_failure(
            phase="failure",
            file="tests/unit/test_service.py",
            message="plain mismatch",
            classifier_config_path=config,
        )
        == "custom_assertion"
    )


def test_build_run_plan_for_direct_lane_adds_single_junit_xml(
    tmp_path: Path,
) -> None:
    plan = test_health.build_run_plan(
        suite="unit-fast",
        run_id="unit-fast-local",
        reports_dir=tmp_path,
        runner_args=[],
        pytest_extra=["--no-cov"],
        skip_preflight=True,
    )

    assert plan.backend == "run_pytest"
    assert plan.command[:3] == [
        "bash",
        "scripts/engineering/dev/run_pytest.sh",
        "--skip-preflight",
    ]
    assert "tests/unit/" in plan.command
    assert "--no-cov" in plan.command
    assert plan.command[-1].endswith("junit/unit-fast-local.xml")
    assert plan.junit_paths == [tmp_path / "junit" / "unit-fast-local.xml"]


def test_build_run_plan_for_sharded_lane_uses_junit_dir_without_lane_paths(
    tmp_path: Path,
) -> None:
    plan = test_health.build_run_plan(
        suite="architecture",
        run_id="architecture-local",
        reports_dir=tmp_path,
        runner_args=["--stream"],
        pytest_extra=["-k", "TestCanonicalTestLanes"],
        skip_preflight=True,
    )

    assert plan.backend == "run_pytest_sharded"
    assert "--junit-dir" in plan.command
    assert plan.junit_dir == tmp_path / "junit" / "architecture-local"
    separator = plan.command.index("--")
    pytest_args = plan.command[separator + 1 :]
    assert "tests/architecture/" not in pytest_args
    assert pytest_args[-2:] == ["-k", "TestCanonicalTestLanes"]


def test_rollup_reads_recent_run_summaries(tmp_path: Path, capsys) -> None:
    summary = {
        "run_id": "unit-fast-1",
        "suite": "unit-fast",
        "exit_code": 1,
        "counts": {
            "failed": 1,
            "errors": 0,
            "skipped": 2,
        },
        "failures": [
            {
                "nodeid": "tests/unit/test_sample.py::test_fail",
                "classification": "assertion",
            }
        ],
    }
    (tmp_path / "unit-fast-1.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    markdown_out = tmp_path / "rollup.md"

    rc = test_health.main(
        [
            "test-health",
            "--reports-dir",
            str(tmp_path),
            "--last",
            "5",
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert (
        "unit-fast: runs=1 non_green=1 pass_rate=0.0% "
        "test_failures=1 unique_failing_tests=1 skipped=2"
    ) in output
    assert "assertion: 1" in output
    assert "unit-fast: tests/unit/test_sample.py::test_fail" in output
    assert "1x tests/unit/test_sample.py::test_fail" in output
    markdown = markdown_out.read_text(encoding="utf-8")
    assert "# Test Health Rollup" in markdown
    assert "| unit-fast | 1 | 1 | 0.0% | 1 | 1 | 2 |" in markdown
    assert "- `assertion`: 1" in markdown


def test_summarize_junit_writes_test_health_json(tmp_path: Path) -> None:
    junit = tmp_path / "junit-fast.xml"
    junit.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
  <testcase classname="tests.unit.test_sample" name="test_pass" file="tests/unit/test_sample.py" />
</testsuite>
""",
        encoding="utf-8",
    )

    rc = test_health.main(
        [
            "summarize-junit",
            "--suite",
            "unit-fast",
            "--run-id",
            "unit-fast-ci",
            "--reports-dir",
            str(tmp_path / "runs"),
            "--junit-glob",
            str(tmp_path / "*.xml"),
            "--command",
            "pytest tests/unit",
        ]
    )

    summary = json.loads(
        (tmp_path / "runs" / "unit-fast-ci.json").read_text(encoding="utf-8")
    )
    assert rc == 0
    assert summary["suite"] == "unit-fast"
    assert summary["counts"]["passed"] == 1
    assert summary["command"] == "pytest tests/unit"


def test_test_health_can_summarize_junit_before_rollup(tmp_path: Path, capsys) -> None:
    junit = tmp_path / "junit" / "S1-domain-core.xml"
    junit.parent.mkdir()
    junit.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
  <testcase classname="tests.unit.test_sample" name="test_pass" file="tests/unit/test_sample.py" />
</testsuite>
""",
        encoding="utf-8",
    )
    markdown_out = tmp_path / "runs" / "rollup.md"

    rc = test_health.main(
        [
            "test-health",
            "--suite",
            "coverage-verify",
            "--run-id",
            "coverage-verify-local",
            "--reports-dir",
            str(tmp_path / "runs"),
            "--junit-glob",
            str(junit.parent / "*.xml"),
            "--last",
            "30",
            "--markdown-out",
            str(markdown_out),
        ]
    )

    summary = json.loads(
        (tmp_path / "runs" / "coverage-verify-local.json").read_text(encoding="utf-8")
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert summary["suite"] == "coverage-verify"
    assert summary["counts"]["passed"] == 1
    assert "Test health rollup: last 1 runs" in output
    assert "| coverage-verify | 1 | 0 | 100.0% | 0 | 0 | 0 |" in (
        markdown_out.read_text(encoding="utf-8")
    )


def test_build_rollup_reports_flaky_candidates_and_pass_rate() -> None:
    runs = [
        {
            "suite": "unit-fast",
            "exit_code": 0,
            "counts": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0},
            "cases": [
                {"nodeid": "tests/unit/test_sample.py::test_flaky", "status": "passed"}
            ],
            "failures": [],
        },
        {
            "suite": "unit-fast",
            "exit_code": 1,
            "counts": {"passed": 0, "failed": 1, "errors": 0, "skipped": 0},
            "cases": [
                {"nodeid": "tests/unit/test_sample.py::test_flaky", "status": "failed"}
            ],
            "failures": [
                {
                    "nodeid": "tests/unit/test_sample.py::test_flaky",
                    "classification": "assertion",
                }
            ],
        },
    ]

    rollup = test_health.build_rollup(runs)

    assert rollup["suites"]["unit-fast"]["pass_rate"] == 0.5
    assert rollup["suites"]["unit-fast"]["unique_failing_tests"] == 1
    assert rollup["flaky_candidates"] == ["tests/unit/test_sample.py::test_flaky"]
