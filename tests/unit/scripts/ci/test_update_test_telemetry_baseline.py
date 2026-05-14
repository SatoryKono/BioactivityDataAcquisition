"""Unit tests for test telemetry baseline updater."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.ci.update_test_telemetry_baseline import (
    _read_coverage_percent,
    _read_coverage_percent_from_log,
    _derive_slowest_summary_from_junit_paths,
    _read_slowest_summary,
    build_baseline_payload,
    render_baseline_markdown,
    write_baseline_outputs,
)


def test_read_coverage_percent_returns_percentage(tmp_path: Path) -> None:
    coverage_xml = tmp_path / "coverage.xml"
    coverage_xml.write_text(
        '<coverage version="7.0" line-rate="0.8765"></coverage>',
        encoding="utf-8",
    )

    assert _read_coverage_percent(coverage_xml) == pytest.approx(87.65)


def test_read_slowest_summary_returns_empty_shape_when_missing(tmp_path: Path) -> None:
    payload = _read_slowest_summary(tmp_path / "missing.json")

    assert payload == {"total_cases": None, "top_slowest": []}


def test_read_coverage_percent_from_log_returns_percentage(tmp_path: Path) -> None:
    coverage_log = tmp_path / "parallel.log"
    coverage_log.write_text(
        "TOTAL  42248  2218  8880  1084  92.81%\n",
        encoding="utf-8",
    )

    assert _read_coverage_percent_from_log(coverage_log) == pytest.approx(92.81)


def test_derive_slowest_summary_from_junit_paths(tmp_path: Path) -> None:
    junit_path = tmp_path / "junit_parallel.xml"
    junit_path.write_text(
        """
<testsuites>
  <testsuite name="suite">
    <testcase classname="tests.example" name="test_fast" time="0.200" />
    <testcase classname="tests.example" name="test_slow" time="5.500" />
  </testsuite>
</testsuites>
""".strip(),
        encoding="utf-8",
    )

    payload = _derive_slowest_summary_from_junit_paths([junit_path])

    assert payload["total_cases"] == 2
    assert payload["top_slowest"][0]["test"] == "tests.example::test_slow"
    assert payload["top_slowest"][0]["duration_s"] == pytest.approx(5.5)


def test_build_baseline_payload_captures_artifact_metrics(tmp_path: Path) -> None:
    coverage_xml = tmp_path / "coverage.xml"
    coverage_xml.write_text(
        '<coverage version="7.0" line-rate="0.9123"></coverage>',
        encoding="utf-8",
    )
    slowest_json = tmp_path / "slowest-tests.json"
    slowest_json.write_text(
        json.dumps(
            {
                "total_cases": 321,
                "top_slowest": [
                    {
                        "source": "junit-fast.xml",
                        "test": "tests.example::test_case",
                        "duration_s": 12.345,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = build_baseline_payload(
        coverage_xml_path=coverage_xml,
        coverage_percent=None,
        coverage_log_path=tmp_path / "parallel.log",
        slowest_json_path=slowest_json,
        junit_paths=[],
        source_branch="main",
        source_commit="abc123",
        source_run_id="run-42",
        coverage_threshold=85.0,
    )

    assert payload["refresh_status"] == "captured"
    assert payload["coverage"]["actual_percent"] == pytest.approx(91.23)
    assert payload["coverage"]["threshold_satisfied"] is True
    assert payload["duration_telemetry"]["total_cases"] == 321
    assert payload["duration_telemetry"]["top_slowest"][0]["test"] == (
        "tests.example::test_case"
    )


def test_render_and_write_baseline_outputs(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "policy_scope": "test_telemetry_baseline",
        "workflow_path": ".github/workflows/tests.yml",
        "source_branch": "main",
        "refreshed_at_utc": "2026-04-29T12:00:00+00:00",
        "refresh_status": "captured",
        "source_commit": "abc123",
        "source_run_id": "run-42",
        "artifact_inputs": {
            "coverage_xml": "reports/coverage/coverage.xml",
            "slowest_tests_json": "reports/test-telemetry/slowest-tests.json",
        },
        "coverage": {
            "threshold_percent": 85.0,
            "actual_percent": 91.23,
            "threshold_satisfied": True,
        },
        "duration_telemetry": {
            "total_cases": 321,
            "top_slowest": [
                {
                    "source": "junit-fast.xml",
                    "test": "tests.example::test_case",
                    "duration_s": 12.345,
                }
            ],
        },
    }

    markdown = render_baseline_markdown(payload)
    assert "Test Telemetry Baseline" in markdown
    assert "`91.23%`" in markdown
    assert "`tests.example::test_case`" in markdown
    assert "`coverage-verify`" in markdown
    assert "historical `test-health` rollups remain non-blocking" in markdown

    output_yaml = tmp_path / "baseline.yaml"
    output_md = tmp_path / "baseline.md"
    write_baseline_outputs(
        payload=payload,
        output_yaml_path=output_yaml,
        output_md_path=output_md,
    )

    assert output_yaml.exists()
    assert output_md.exists()
    assert "test_telemetry_baseline" in output_yaml.read_text(encoding="utf-8")
    assert "Test Telemetry Baseline" in output_md.read_text(encoding="utf-8")


def test_build_baseline_payload_marks_duration_only_refresh_as_captured(
    tmp_path: Path,
) -> None:
    slowest_json = tmp_path / "slowest-tests.json"
    slowest_json.write_text(
        json.dumps({"total_cases": 0, "top_slowest": []}),
        encoding="utf-8",
    )

    payload = build_baseline_payload(
        coverage_xml_path=tmp_path / "missing-coverage.xml",
        coverage_percent=None,
        coverage_log_path=tmp_path / "missing-parallel.log",
        slowest_json_path=slowest_json,
        junit_paths=[],
        source_branch="main",
        source_commit="abc123",
        source_run_id="run-42",
        coverage_threshold=85.0,
    )

    assert payload["refresh_status"] == "captured"
    assert payload["duration_telemetry"]["total_cases"] == 0


def test_build_baseline_payload_uses_fallback_coverage_and_junit(tmp_path: Path) -> None:
    coverage_log = tmp_path / "parallel.log"
    coverage_log.write_text(
        "TOTAL  42248  2218  8880  1084  92.81%\n",
        encoding="utf-8",
    )
    junit_path = tmp_path / "junit_parallel.xml"
    junit_path.write_text(
        """
<testsuites>
  <testsuite name="suite">
    <testcase classname="tests.example" name="test_fast" time="0.200" />
    <testcase classname="tests.example" name="test_slow" time="5.500" />
  </testsuite>
</testsuites>
""".strip(),
        encoding="utf-8",
    )

    payload = build_baseline_payload(
        coverage_xml_path=tmp_path / "missing-coverage.xml",
        coverage_percent=None,
        coverage_log_path=coverage_log,
        slowest_json_path=tmp_path / "missing-slowest.json",
        junit_paths=[junit_path],
        source_branch="main",
        source_commit="abc123",
        source_run_id="run-42",
        coverage_threshold=85.0,
    )

    assert payload["refresh_status"] == "captured"
    assert payload["coverage"]["actual_percent"] == pytest.approx(92.81)
    assert payload["coverage"]["threshold_satisfied"] is True
    assert payload["duration_telemetry"]["total_cases"] == 2
    assert payload["artifact_inputs"]["junit_inputs"] == [str(junit_path)]
