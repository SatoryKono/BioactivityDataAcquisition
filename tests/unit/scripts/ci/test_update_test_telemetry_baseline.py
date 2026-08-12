# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for test telemetry baseline updater."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.ci.update_test_telemetry_baseline import (
    build_branch_telemetry_reports,
    _extract_slowest_zone,
    _summarize_slowest_zones,
    _read_coverage_percent,
    _read_coverage_percent_from_log,
    _derive_slowest_summary_from_junit_paths,
    _read_slowest_summary,
    build_baseline_payload,
    merge_existing_baseline_supplemental_fields,
    render_baseline_markdown,
    write_baseline_outputs,
)


pytestmark = pytest.mark.unit


def test_read_coverage_percent_returns_percentage(tmp_path: Path) -> None:
    coverage_xml = tmp_path / "coverage.xml"
    coverage_xml.write_text(
        '<coverage version="7.0" line-rate="0.8765"></coverage>',
        encoding="utf-8",
    )

    assert _read_coverage_percent(coverage_xml) == pytest.approx(87.65)


def test_read_slowest_summary_returns_empty_shape_when_missing(tmp_path: Path) -> None:
    payload = _read_slowest_summary(tmp_path / "missing.json")

    assert payload == {
        "total_cases": None,
        "top_slowest": [],
        "execution_context": {},
    }


def test_read_slowest_summary_accepts_compatibility_alias(tmp_path: Path) -> None:
    slowest_json = tmp_path / "slowest-tests.json"
    slowest_json.write_text(
        json.dumps(
            {
                "total_cases": 1,
                "top_slowest_tests": [
                    {
                        "source": "junit.xml",
                        "test": "tests.example::test_case",
                        "duration_s": 1.234,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = _read_slowest_summary(slowest_json)

    assert payload["total_cases"] == 1
    assert payload["top_slowest"] == [
        {
            "source": "junit.xml",
            "test": "tests.example::test_case",
            "duration_s": 1.234,
        }
    ]


def test_read_slowest_summary_backfills_missing_lane_duration_provenance(
    tmp_path: Path,
) -> None:
    slowest_json = tmp_path / "slowest-tests.json"
    slowest_json.write_text(
        json.dumps(
            {
                "total_cases": 1,
                "top_slowest": [],
                "execution_context": {
                    "junit_testcase_duration_sum_s": {"junit-fast.xml": 12.5}
                },
            }
        ),
        encoding="utf-8",
    )

    context = _read_slowest_summary(slowest_json)["execution_context"]

    assert context["lane_wall_time_s"] == {"junit-fast.xml": 12.5}
    assert context["lane_wall_time_source"] == "junit_testcase_duration_sum_fallback"


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


def test_summarize_slowest_zones_groups_cases_by_module() -> None:
    rows = [
        {
            "source": "junit-fast.xml",
            "test": "tests.alpha.test_mod::test_fast",
            "duration_s": 1.25,
        },
        {
            "source": "junit-fast.xml",
            "test": "tests.alpha.test_mod::test_slow",
            "duration_s": 3.75,
        },
        {
            "source": "junit-fast.xml",
            "test": "tests.beta.test_other::test_case",
            "duration_s": 2.0,
        },
    ]

    assert _extract_slowest_zone(rows[0]["test"]) == "tests.alpha.test_mod"
    assert _summarize_slowest_zones(rows) == [
        {
            "zone": "tests.alpha.test_mod",
            "test_count": 2,
            "total_duration_s": 5.0,
            "max_duration_s": 3.75,
        },
        {
            "zone": "tests.beta.test_other",
            "test_count": 1,
            "total_duration_s": 2.0,
            "max_duration_s": 2.0,
        },
    ]


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
    assert payload["freshness_guard"]["timestamp_field"] == "refreshed_at_utc"
    assert payload["freshness_guard"]["max_age_days"] == 45
    assert payload["duration_telemetry"]["total_cases"] == 321
    assert payload["duration_telemetry"]["top_slowest"][0]["test"] == (
        "tests.example::test_case"
    )
    assert payload["duration_telemetry"]["top_slowest_zones"] == [
        {
            "zone": "tests.example",
            "test_count": 1,
            "total_duration_s": 12.345,
            "max_duration_s": 12.345,
        }
    ]


def test_build_baseline_payload_keeps_repo_inputs_portable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Committed provenance must not contain checkout-specific absolute paths."""
    monkeypatch.chdir(tmp_path)
    coverage_xml = tmp_path / "reports/coverage/coverage.xml"
    slowest_json = tmp_path / "reports/test-telemetry/slowest-tests.json"

    payload = build_baseline_payload(
        coverage_xml_path=coverage_xml,
        coverage_percent=92.44,
        coverage_log_path=None,
        slowest_json_path=slowest_json,
        junit_paths=[],
        source_branch="main",
        source_commit="abc123",
        source_run_id="run-42",
        coverage_threshold=85.0,
    )

    assert payload["artifact_inputs"] == {
        "coverage_xml": "reports/coverage/coverage.xml",
        "coverage_log": None,
        "coverage_percent_fallback": 92.44,
        "slowest_tests_json": "reports/test-telemetry/slowest-tests.json",
        "junit_inputs": [],
    }


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
        "freshness_guard": {
            "timestamp_field": "refreshed_at_utc",
            "max_age_days": 45,
        },
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
            "top_slowest_zones": [
                {
                    "zone": "tests.example",
                    "test_count": 1,
                    "total_duration_s": 12.345,
                    "max_duration_s": 12.345,
                }
            ],
        },
    }

    markdown = render_baseline_markdown(payload)
    assert "Test Telemetry Baseline" in markdown
    assert "`91.23%`" in markdown
    assert "`tests.example::test_case`" in markdown
    assert "Top Slow Zones" in markdown
    assert "`coverage-verify`" in markdown
    assert "historical `test-health` rollups remain non-blocking" in markdown

    output_yaml = tmp_path / "baseline.yaml"
    output_md = tmp_path / "baseline.md"
    write_baseline_outputs(
        payload=payload,
        output_yaml_path=output_yaml,
        output_md_path=output_md,
        branch_reports_dir=tmp_path / "reports" / "test-telemetry",
    )

    assert output_yaml.exists()
    assert output_md.exists()
    assert "test_telemetry_baseline" in output_yaml.read_text(encoding="utf-8")
    assert "Test Telemetry Baseline" in output_md.read_text(encoding="utf-8")
    slowest_json = tmp_path / "reports" / "test-telemetry" / "slowest-tests.json"
    coverage_summary = tmp_path / "reports" / "test-telemetry" / "coverage-summary.json"
    slowest_md = tmp_path / "reports" / "test-telemetry" / "slowest-tests.md"
    assert slowest_json.exists()
    assert coverage_summary.exists()
    assert slowest_md.exists()
    slowest_payload = json.loads(slowest_json.read_text(encoding="utf-8"))
    assert slowest_payload["total_cases"] == 321
    assert slowest_payload["top_slowest"][0]["test"] == "tests.example::test_case"
    assert slowest_payload["top_slowest_zones"][0]["zone"] == "tests.example"
    coverage_payload = json.loads(coverage_summary.read_text(encoding="utf-8"))
    assert coverage_payload["coverage"]["actual_percent"] == pytest.approx(91.23)
    slowest_markdown = slowest_md.read_text(encoding="utf-8")
    assert "Slowest Tests" in slowest_markdown
    assert "Top Slow Zones" in slowest_markdown


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


def test_build_baseline_payload_uses_fallback_coverage_and_junit(
    tmp_path: Path,
) -> None:
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


def test_build_branch_telemetry_reports_preserves_baseline_snapshot() -> None:
    payload = {
        "source_branch": "main",
        "source_commit": "abc123",
        "source_run_id": "run-42",
        "refreshed_at_utc": "2026-04-29T12:00:00+00:00",
        "refresh_status": "captured",
        "freshness_guard": {
            "timestamp_field": "refreshed_at_utc",
            "max_age_days": 45,
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
            "top_slowest_zones": [
                {
                    "zone": "tests.example",
                    "test_count": 1,
                    "total_duration_s": 12.345,
                    "max_duration_s": 12.345,
                }
            ],
        },
    }

    reports = build_branch_telemetry_reports(payload)

    coverage_summary = json.loads(reports["coverage-summary.json"])
    slowest_summary = json.loads(reports["slowest-tests.json"])
    assert coverage_summary["coverage"]["actual_percent"] == pytest.approx(91.23)
    assert coverage_summary["coverage_percent"] == pytest.approx(91.23)
    assert slowest_summary["total_cases"] == 321
    assert slowest_summary["top_slowest"][0]["test"] == "tests.example::test_case"
    assert slowest_summary["top_slowest_tests"] == slowest_summary["top_slowest"]
    assert slowest_summary["top_slowest_zones"][0]["zone"] == "tests.example"
    assert "Slowest Tests" in reports["slowest-tests.md"]
    assert "Top Slow Zones" in reports["slowest-tests.md"]


def test_merge_existing_baseline_supplemental_fields_preserves_probe(
    tmp_path: Path,
) -> None:
    existing_yaml = tmp_path / "baseline.yaml"
    existing_yaml.write_text(
        json.dumps(
            {
                "slow_governance_cache_probe": {
                    "issue_ref": "#4663",
                    "source": "local_direct_probe",
                }
            }
        ),
        encoding="utf-8",
    )

    payload = merge_existing_baseline_supplemental_fields(
        {"policy_scope": "test_telemetry_baseline"},
        existing_yaml_path=existing_yaml,
    )

    assert payload["slow_governance_cache_probe"] == {
        "issue_ref": "#4663",
        "source": "local_direct_probe",
    }
