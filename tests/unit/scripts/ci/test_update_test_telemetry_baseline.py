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

import copy
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts.engineering.ci import test_telemetry_provenance as provenance
from scripts.engineering.ci import update_test_telemetry_baseline as updater
from scripts.engineering.ci.junit_duration_summary import write_ci_summary

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


def test_junit_counts_observed_non_skipped_records_independent_of_time(
    tmp_path: Path,
) -> None:
    junit_path = tmp_path / "nested.xml"
    junit_path.write_text(
        """<testsuites tests="8" skipped="1">
  <testsuite name="outer">
    <testcase classname="suite" name="passed" time="1.5" />
    <testcase classname="suite" name="zero" time="0" />
    <testcase classname="suite" name="missing" />
    <testcase classname="suite" name="skipped" time="4"><skipped /></testcase>
    <testsuite name="inner">
      <testcase classname="suite" name="failed" time="0"><failure /></testcase>
      <testcase classname="suite" name="errored"><error /></testcase>
      <testcase classname="suite" name="retry" time="0.2" />
      <testcase classname="suite" name="retry" time="0.3" />
    </testsuite>
  </testsuite>
</testsuites>""",
        encoding="utf-8",
    )

    payload = _derive_slowest_summary_from_junit_paths([junit_path])

    assert payload["total_cases"] == 7
    assert payload["execution_context"]["executed_count"] == 7
    assert [row["duration_s"] for row in payload["top_slowest"]] == [
        1.5,
        0.3,
        0.2,
    ]
    assert [row["test"] for row in payload["top_slowest"]].count("suite::retry") == 2


@pytest.mark.parametrize(
    ("testcases", "expected"),
    [
        ("", 0),
        ('<testcase name="skip" time="5"><skipped /></testcase>', 0),
    ],
)
def test_junit_empty_or_only_skipped_has_no_executed_cases(
    tmp_path: Path, testcases: str, expected: int
) -> None:
    junit_path = tmp_path / "junit.xml"
    junit_path.write_text(
        f'<testsuite tests="{int(bool(testcases))}" skipped="{int(bool(testcases))}">'
        f"{testcases}</testsuite>",
        encoding="utf-8",
    )
    payload = _derive_slowest_summary_from_junit_paths([junit_path])
    assert payload["total_cases"] == expected
    assert payload["top_slowest"] == []


@pytest.mark.parametrize("bad_time", ["bogus", "NaN", "inf", "-1", ""])
def test_junit_rejects_invalid_duration_without_losing_case(
    tmp_path: Path, bad_time: str
) -> None:
    junit_path = tmp_path / "invalid.xml"
    junit_path.write_text(
        f'<testsuite><testcase name="case" time="{bad_time}" /></testsuite>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duration"):
        _derive_slowest_summary_from_junit_paths([junit_path])


def test_junit_rejects_aggregate_test_count_disagreement(tmp_path: Path) -> None:
    junit_path = tmp_path / "mismatch.xml"
    junit_path.write_text(
        '<testsuite tests="2"><testcase name="only" time="1" /></testsuite>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="testcase count"):
        _derive_slowest_summary_from_junit_paths([junit_path])


def test_junit_suite_level_error_does_not_invent_testcase(tmp_path: Path) -> None:
    junit_path = tmp_path / "suite-error.xml"
    junit_path.write_text(
        '<testsuite tests="0" errors="1"><error message="collection" /></testsuite>',
        encoding="utf-8",
    )
    payload = _derive_slowest_summary_from_junit_paths([junit_path])
    assert payload["total_cases"] == 0
    assert payload["top_slowest"] == []


@pytest.mark.parametrize("declared", [1, 2])
def test_junit_suite_totals_accept_record_or_diagnostic_counts(
    tmp_path: Path, declared: int
) -> None:
    path = tmp_path / "multiple-diagnostics.xml"
    path.write_text(
        f'<testsuites tests="1" errors="{declared}" failures="{declared}">'
        f'<testsuite tests="1" errors="{declared}" failures="{declared}">'
        '<testcase name="multiple_diagnostics" time="0">'
        '<error message="setup" /><error message="teardown" />'
        '<failure message="first" /><failure message="second" />'
        "</testcase></testsuite></testsuites>",
        encoding="utf-8",
    )
    summary = _derive_slowest_summary_from_junit_paths([path])
    assert summary["total_cases"] == 1
    assert summary["execution_context"]["observed_count"] == 1
    # The context always counts affected records, regardless of suite convention.
    assert summary["execution_context"]["error_record_count"] == 1
    assert summary["execution_context"]["failure_record_count"] == 1


def test_junit_rejects_aggregate_outside_both_count_conventions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "contradictory.xml"
    path.write_text(
        '<testsuite tests="1" errors="3"><testcase name="double_error">'
        "<error /><error /></testcase></testsuite>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="JUnit errors testcase count disagrees"):
        _derive_slowest_summary_from_junit_paths([path])


def test_workflow_producer_and_fallback_share_record_contract(tmp_path: Path) -> None:
    raw = tmp_path / "reports/test-telemetry/raw"
    raw.mkdir(parents=True)
    (raw / "lane.xml").write_text(
        """<testsuites tests="7" skipped="2" errors="1" failures="1">
  <testsuite tests="7" skipped="2" errors="1" failures="1" time="9">
    <testcase classname="suite" name="positive" time="2" />
    <testcase classname="suite" name="zero" time="0" />
    <testcase classname="suite" name="missing" />
    <testcase classname="suite" name="skip" time="5"><skipped /></testcase>
    <testcase classname="suite" name="skip_error" time="4"><skipped /><error /></testcase>
    <testcase classname="suite" name="retry" time="1"><failure /></testcase>
    <testcase classname="suite" name="retry" time="1.5" />
  </testsuite>
</testsuites>""",
        encoding="utf-8",
    )
    # This is the exact module invocation used by tests.yml, in a fixture cwd.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(updater.REPO_ROOT)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.ci.junit_duration_summary",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    produced = json.loads(
        (tmp_path / "reports/test-telemetry/slowest-tests.json").read_text(
            encoding="utf-8"
        )
    )
    fallback = _derive_slowest_summary_from_junit_paths([raw / "lane.xml"])
    assert produced["total_cases"] == fallback["total_cases"] == 5
    assert produced["top_slowest"] == fallback["top_slowest"]
    assert produced["execution_context"]["observed_count"] == 7
    assert produced["execution_context"]["skipped_count"] == 2
    assert produced["execution_context"]["error_record_count"] == 1
    assert produced["execution_context"]["junit_testcase_duration_sum_s"] == {
        "lane.xml": 13.5
    }
    assert produced["execution_context"]["lane_wall_time_s"] == {"lane.xml": 9.0}
    assert [row["test"] for row in produced["top_slowest"]].count("suite::retry") == 2
    markdown = (tmp_path / "reports/test-telemetry/slowest-tests.md").read_text(
        encoding="utf-8"
    )
    assert "Observed testcase records: `7`" in markdown
    assert "Non-skipped testcase records: `5`" in markdown
    assert "Collected test cases" not in markdown


@pytest.mark.parametrize("flag", ["--raw-dir", "--output-dir"])
def test_workflow_producer_rejects_path_arguments(tmp_path: Path, flag: str) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("untouched", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(updater.REPO_ROOT)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.ci.junit_duration_summary",
            flag,
            str(outside),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert sentinel.read_text(encoding="utf-8") == "untouched"
    assert not (tmp_path / "reports/test-telemetry").exists()


@pytest.mark.parametrize(
    "xml",
    [
        '<testsuites><testsuite tests="2"><testcase name="one" /></testsuite></testsuites>',
        '<testsuites><testsuite skipped="1"><testcase name="one" /></testsuite></testsuites>',
        '<testsuites tests="1"><testsuite tests="1" errors="1"><testcase name="one" /></testsuite></testsuites>',
        '<testsuites tests="2"><testsuite tests="1"><testcase name="one" /></testsuite></testsuites>',
    ],
)
def test_nested_suite_aggregates_are_checked_without_double_count(
    tmp_path: Path,
    xml: str,
) -> None:
    path = tmp_path / "bad.xml"
    path.write_text(xml, encoding="utf-8")
    with pytest.raises(ValueError, match="testcase count"):
        _derive_slowest_summary_from_junit_paths([path])


def test_zero_only_is_present_telemetry_in_both_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    raw = tmp_path / "reports/test-telemetry/raw"
    raw.mkdir(parents=True)
    (raw / "zero.xml").write_text(
        '<testsuite tests="2"><testcase name="zero" time="0" />'
        '<testcase name="missing" /></testsuite>',
        encoding="utf-8",
    )
    summary = write_ci_summary()
    assert summary["total_cases"] == 2
    assert summary["top_slowest"] == []
    assert "records are present" in (
        tmp_path / "reports/test-telemetry/slowest-tests.md"
    ).read_text(encoding="utf-8")
    payload = build_baseline_payload(
        coverage_xml_path=tmp_path / "missing.xml",
        coverage_percent=None,
        coverage_log_path=None,
        slowest_json_path=tmp_path / "reports/test-telemetry/slowest-tests.json",
        junit_paths=[],
        source_branch="main",
        source_commit="source",
        source_run_id="run",
        coverage_threshold=85.0,
    )
    assert "records are present" in render_baseline_markdown(payload)
    assert (
        "records are present"
        in build_branch_telemetry_reports(payload)["slowest-tests.md"]
    )


@pytest.mark.parametrize(
    ("cases", "observed", "skipped", "message"),
    [
        ("", 0, 0, "no testcase records"),
        (
            '<testcase name="skip" time="2"><skipped /></testcase>',
            1,
            1,
            "records are present",
        ),
    ],
)
def test_empty_and_all_skipped_telemetry_are_distinct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cases: str,
    observed: int,
    skipped: int,
    message: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    raw = tmp_path / "reports/test-telemetry/raw"
    raw.mkdir(parents=True)
    (raw / "lane.xml").write_text(
        f'<testsuite tests="{observed}" skipped="{skipped}">{cases}</testsuite>',
        encoding="utf-8",
    )
    summary = write_ci_summary()
    assert summary["execution_context"]["observed_count"] == observed
    assert summary["execution_context"]["skipped_count"] == skipped
    assert summary["total_cases"] == 0
    assert summary["top_slowest"] == []
    payload = build_baseline_payload(
        coverage_xml_path=tmp_path / "missing.xml",
        coverage_percent=None,
        coverage_log_path=None,
        slowest_json_path=tmp_path / "reports/test-telemetry/slowest-tests.json",
        junit_paths=[],
        source_branch="main",
        source_commit="source",
        source_run_id="run",
        coverage_threshold=85.0,
    )
    assert message in render_baseline_markdown(payload)
    assert message in build_branch_telemetry_reports(payload)["slowest-tests.md"]


def test_missing_junit_source_is_not_an_empty_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    summary = write_ci_summary()
    assert summary["total_cases"] is None
    assert summary["execution_context"]["junit_source_count"] == 0
    payload = build_baseline_payload(
        coverage_xml_path=tmp_path / "missing.xml",
        coverage_percent=None,
        coverage_log_path=None,
        slowest_json_path=tmp_path / "reports/test-telemetry/slowest-tests.json",
        junit_paths=[],
        source_branch="main",
        source_commit="source",
        source_run_id="run",
        coverage_threshold=85.0,
    )
    assert payload["refresh_status"] == "pending_initial_refresh"
    assert "No JUnit telemetry sources are available" in render_baseline_markdown(
        payload
    )


def test_legacy_json_count_is_timed_rows_or_recomputed_with_junit(
    tmp_path: Path,
) -> None:
    legacy = tmp_path / "slowest.json"
    legacy.write_text(
        json.dumps(
            {
                "total_cases": 1,
                "top_slowest": [],
                "execution_context": {
                    "executed_count": 1,
                    "junit_source_count": 1,
                    "junit_sources": ["junit.xml"],
                },
            }
        ),
        encoding="utf-8",
    )
    raw = tmp_path / "junit.xml"
    raw.write_text(
        '<testsuite tests="2"><testcase name="timed" time="1" />'
        '<testcase name="zero" time="0" /></testsuite>',
        encoding="utf-8",
    )
    kwargs = {
        "coverage_xml_path": tmp_path / "missing.xml",
        "coverage_percent": None,
        "coverage_log_path": None,
        "slowest_json_path": legacy,
        "source_branch": "main",
        "source_commit": "source",
        "source_run_id": "run",
        "coverage_threshold": 85.0,
    }
    old = build_baseline_payload(junit_paths=[], **kwargs)
    assert old["duration_telemetry"]["total_cases"] == 1
    assert (
        old["duration_telemetry"]["count_semantics"] == "legacy_positive_duration_rows"
    )
    assert "executed_count" not in old["duration_telemetry"]["execution_context"]
    assert "Legacy positive-duration testcase rows: `1`" in render_baseline_markdown(
        old
    )
    assert (
        "Legacy positive-duration testcase rows: `1`"
        in build_branch_telemetry_reports(old)["slowest-tests.md"]
    )
    rebound = build_baseline_payload(junit_paths=[raw], **kwargs)
    assert rebound["duration_telemetry"]["total_cases"] == 2
    assert (
        rebound["duration_telemetry"]["count_semantics"] == "non_skipped_junit_records"
    )


def test_legacy_only_refresh_rejects_before_overwriting_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    legacy = tmp_path / "slowest.json"
    legacy.write_text(json.dumps({"total_cases": 1}), encoding="utf-8")
    baseline = tmp_path / "baseline.yaml"
    baseline.write_text("existing baseline", encoding="utf-8")
    rendered = tmp_path / "baseline.md"
    monkeypatch.setattr(updater, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        "scripts.engineering.common.repo_paths.resolve_output_path", Path
    )
    monkeypatch.setattr(
        updater,
        "_parse_args",
        lambda: SimpleNamespace(
            rebind_current_tree=False,
            local_manifest=None,
            source_commit="source",
            source_run_id="run",
            source_run_url="",
            source_branch="main",
            source_event="push",
            coverage_percent=85.0,
            coverage_xml=tmp_path / "missing.xml",
            coverage_log="",
            slowest_json=legacy,
            junit=[],
            coverage_threshold=None,
            output_yaml=baseline,
            output_md=rendered,
        ),
    )
    with pytest.raises(ValueError, match="requires --junit inputs"):
        updater.main()
    assert baseline.read_text(encoding="utf-8") == "existing baseline"
    assert not rendered.exists()


def test_source_tree_hash_includes_live_junit_producer(tmp_path: Path) -> None:
    producer = tmp_path / "scripts/engineering/ci/junit_duration_summary.py"
    producer.parent.mkdir(parents=True)
    producer.write_text("first\n", encoding="utf-8")
    first = updater.compute_test_telemetry_source_tree_sha256(tmp_path)
    producer.write_text("second\n", encoding="utf-8")
    assert updater.compute_test_telemetry_source_tree_sha256(tmp_path) != first


def test_markerless_canonical_local_json_preserves_non_skipped_semantics(
    tmp_path: Path,
) -> None:
    local = tmp_path / "local.json"
    local.write_text(
        json.dumps(
            {
                "source_event": "local_coverage_verify",
                "source_run_id": "local-measurement",
                "measurement_provenance": {
                    "producer": "run_local_coverage_verify.py",
                    "complete": True,
                },
                "total_cases": 2,
                "top_slowest": [],
                "execution_context": {"executed_count": 2, "skipped_count": 1},
            }
        ),
        encoding="utf-8",
    )
    summary = _read_slowest_summary(local)
    assert summary["total_cases"] == 2
    assert summary["execution_context"]["executed_count"] == 2
    assert (
        summary["execution_context"]["count_semantics"] == "non_skipped_junit_records"
    )


@pytest.mark.parametrize(
    ("bad_total", "observed", "skipped", "executed"),
    [(2, 3, 2, 2), (True, 1, 0, 1), (1.0, 1, 0, 1)],
)
def test_marked_json_rejects_inconsistent_record_counts(
    tmp_path: Path,
    bad_total: object,
    observed: int,
    skipped: int,
    executed: int,
) -> None:
    summary = tmp_path / "marked.json"
    summary.write_text(
        json.dumps(
            {
                "total_cases": bad_total,
                "execution_context": {
                    "count_semantics": "non_skipped_junit_records",
                    "observed_count": observed,
                    "skipped_count": skipped,
                    "executed_count": executed,
                    "junit_source_count": 1,
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Inconsistent non-skipped JUnit counts"):
        _read_slowest_summary(summary)


def test_marked_local_capture_also_validates_record_counts(tmp_path: Path) -> None:
    summary = tmp_path / "local-marked.json"
    summary.write_text(
        json.dumps(
            {
                "source_event": "local_coverage_verify",
                "measurement_provenance": {
                    "producer": "run_local_coverage_verify.py",
                    "complete": True,
                },
                "total_cases": 1,
                "execution_context": {
                    "count_semantics": "non_skipped_junit_records",
                    "observed_count": 4,
                    "skipped_count": 0,
                    "executed_count": 1,
                    "junit_source_count": 1,
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Inconsistent non-skipped JUnit counts"):
        _read_slowest_summary(summary)


def test_incomplete_junit_inputs_cannot_recompute_legacy_count(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.json"
    legacy.write_text(
        json.dumps({"total_cases": 1, "top_slowest": []}), encoding="utf-8"
    )
    present = tmp_path / "present.xml"
    present.write_text(
        '<testsuite tests="1"><testcase name="zero" time="0" /></testsuite>',
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError, match="Missing JUnit telemetry input"):
        build_baseline_payload(
            coverage_xml_path=tmp_path / "missing.xml",
            coverage_percent=None,
            coverage_log_path=None,
            slowest_json_path=legacy,
            junit_paths=[present, tmp_path / "missing.xml"],
            source_branch="main",
            source_commit="source",
            source_run_id="run",
            coverage_threshold=85.0,
        )


def test_partial_existing_junit_inventory_cannot_replace_full_summary(
    tmp_path: Path,
) -> None:
    legacy = tmp_path / "legacy.json"
    legacy.write_text(
        json.dumps(
            {
                "total_cases": 1,
                "top_slowest": [],
                "execution_context": {
                    "junit_source_count": 2,
                    "junit_sources": ["first.xml", "second.xml"],
                },
            }
        ),
        encoding="utf-8",
    )
    first = tmp_path / "first.xml"
    second = tmp_path / "second.xml"
    first.write_text('<testsuite tests="1"><testcase name="first" /></testsuite>')
    second.write_text('<testsuite tests="1"><testcase name="second" /></testsuite>')
    kwargs = {
        "coverage_xml_path": tmp_path / "missing.xml",
        "coverage_percent": None,
        "coverage_log_path": None,
        "slowest_json_path": legacy,
        "source_branch": "main",
        "source_commit": "source",
        "source_run_id": "run",
        "coverage_threshold": 85.0,
    }
    with pytest.raises(ValueError, match="refusing a partial refresh"):
        build_baseline_payload(**kwargs, junit_paths=[first])
    payload = build_baseline_payload(**kwargs, junit_paths=[first, second])
    assert payload["duration_telemetry"]["total_cases"] == 2
    assert payload["duration_telemetry"]["execution_context"]["junit_sources"] == [
        "first.xml",
        "second.xml",
    ]


def test_nested_testsuites_wrapper_preserves_non_overlapping_wall_time(
    tmp_path: Path,
) -> None:
    path = tmp_path / "nested.xml"
    path.write_text(
        '<testsuites><testsuites><testsuite tests="1" time="3">'
        '<testcase name="one" /></testsuite></testsuites>'
        '<testsuite tests="2" time="4"><testcase name="two" />'
        '<testsuite tests="1" time="2"><testcase name="three" />'
        "</testsuite></testsuite></testsuites>",
        encoding="utf-8",
    )
    summary = _derive_slowest_summary_from_junit_paths([path])
    assert summary["total_cases"] == 3
    assert summary["execution_context"]["lane_wall_time_s"] == {"nested.xml": 7.0}


def test_duplicate_junit_paths_and_ambiguous_source_names_fail_closed(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first" / "junit.xml"
    second = tmp_path / "second" / "junit.xml"
    for path in (first, second):
        path.parent.mkdir()
        path.write_text(
            '<testsuite tests="1"><testcase name="one" /></testsuite>',
            encoding="utf-8",
        )
    with pytest.raises(ValueError, match="Duplicate JUnit telemetry input path"):
        _derive_slowest_summary_from_junit_paths([first, first])

    legacy = tmp_path / "legacy.json"
    legacy.write_text(
        json.dumps(
            {
                "total_cases": 1,
                "top_slowest": [],
                "execution_context": {
                    "junit_source_count": 2,
                    "junit_sources": ["junit.xml", "junit.xml"],
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Ambiguous JUnit telemetry source name"):
        build_baseline_payload(
            coverage_xml_path=tmp_path / "missing.xml",
            coverage_percent=None,
            coverage_log_path=None,
            slowest_json_path=legacy,
            junit_paths=[first, second],
            source_branch="main",
            source_commit="source",
            source_run_id="run",
            coverage_threshold=85.0,
        )


def test_pytest_skip_with_teardown_error_is_not_executed(tmp_path: Path) -> None:
    test_file = tmp_path / "test_skip_teardown.py"
    test_file.write_text(
        "import pytest\n"
        "@pytest.fixture\n"
        "def failing_teardown():\n"
        "    yield\n"
        "    raise RuntimeError('teardown failed')\n"
        "def test_skip(failing_teardown):\n"
        "    pytest.skip('skip after fixture setup')\n",
        encoding="utf-8",
    )
    junit = tmp_path / "actual-pytest.xml"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q", f"--junitxml={junit}"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    root = ET.parse(junit).getroot()
    case = next(root.iter("testcase"))
    assert case.find("skipped") is not None
    assert case.find("error") is not None
    suite = root.find("testsuite")
    assert suite is not None
    assert suite.get("tests") == "1"
    assert suite.get("skipped") == "1"
    assert suite.get("errors") == "1"
    summary = _derive_slowest_summary_from_junit_paths([junit])
    assert summary["execution_context"]["observed_count"] == 1
    assert summary["execution_context"]["skipped_count"] == 1
    assert summary["execution_context"]["error_record_count"] == 1
    assert summary["total_cases"] == 0


def test_pytest_double_error_aggregate_keeps_one_record(tmp_path: Path) -> None:
    test_file = tmp_path / "test_double_error.py"
    test_file.write_text(
        "import pytest\n"
        "@pytest.fixture\n"
        "def bad(request):\n"
        "    request.addfinalizer(lambda: 1 / 0)\n"
        "    raise RuntimeError('setup failure')\n"
        "def test_one(bad):\n"
        "    pass\n",
        encoding="utf-8",
    )
    junit = tmp_path / "actual-double-error.xml"
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            str(test_file),
            f"--junitxml={junit}",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    root = ET.parse(junit).getroot()
    suite = root.find("testsuite")
    assert suite is not None
    assert suite.get("tests") == "1"
    assert suite.get("errors") == "2"
    case = next(root.iter("testcase"))
    assert len(case.findall("error")) == 2
    summary = _derive_slowest_summary_from_junit_paths([junit])
    assert summary["execution_context"]["observed_count"] == 1
    assert summary["execution_context"]["error_record_count"] == 1
    assert summary["total_cases"] == 1


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
        source_event="pull_request",
        source_run_url="https://github.example/actions/runs/run-42",
        coverage_threshold=85.0,
    )

    assert payload["refresh_status"] == "captured"
    assert payload["coverage"]["actual_percent"] == pytest.approx(91.23)
    assert payload["coverage"]["threshold_satisfied"] is True
    assert payload["freshness_guard"]["timestamp_field"] == "refreshed_at_utc"
    assert payload["freshness_guard"]["max_age_days"] == 45
    assert payload["source_event"] == "pull_request"
    assert payload["source_run_url"] == "https://github.example/actions/runs/run-42"
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
        "source_event": "push",
        "source_run_url": "https://github.example/actions/runs/run-42",
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
    assert "Source event: `push`" in markdown
    assert "Total executed test cases: `321`" in markdown

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
    assert "Executed test cases: `321`" in slowest_markdown
    assert "Collected test cases" not in slowest_markdown


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
        "source_event": "push",
        "source_run_url": "https://github.example/actions/runs/run-42",
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
    assert coverage_summary["source_event"] == "push"
    assert slowest_summary["source_run_url"].endswith("/run-42")
    assert slowest_summary["total_cases"] == 321
    assert slowest_summary["top_slowest"][0]["test"] == "tests.example::test_case"
    assert slowest_summary["top_slowest_tests"] == slowest_summary["top_slowest"]
    assert slowest_summary["top_slowest_zones"][0]["zone"] == "tests.example"
    assert "Slowest Tests" in reports["slowest-tests.md"]
    assert "Top Slow Zones" in reports["slowest-tests.md"]
    assert "Executed test cases: `321`" in reports["slowest-tests.md"]


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


@pytest.mark.parametrize(
    ("source_event", "message"),
    [
        ("local_coverage_verify", "metrics lack a reviewed binding"),
        ("push", "requires a reviewed local coverage capture"),
        ("pull_request", "requires a reviewed local coverage capture"),
        ("workflow_dispatch", "requires a reviewed local coverage capture"),
        ("schedule", "requires a reviewed local coverage capture"),
    ],
)
def test_rebind_rejects_tampered_or_unverified_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_event: str,
    message: str,
) -> None:
    payload = {
        "source_event": source_event,
        "source_commit": "a" * 40,
        "source_run_id": "local-capture",
        "measurement_provenance": {
            "head": "a" * 40,
            "test_tree_sha256": "measured-tree",
            "manifest_sha256": "manifest-digest",
        },
        "coverage": {"actual_percent": 0.0},
        "duration_telemetry": {"total_cases": 17},
    }
    original = {**payload, "coverage": {"actual_percent": 99.0}}
    receipt = {
        "schema_version": 1,
        "source_commit": payload["source_commit"],
        "source_run_id": payload["source_run_id"],
        "source_tree_sha256": "measured-tree",
        "manifest_sha256": "manifest-digest",
        "metrics_sha256": provenance.telemetry_metrics_sha256(original),
    }
    receipt_path = tmp_path / provenance.RECEIPT
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    baseline_path = tmp_path / "baseline.yaml"
    baseline_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    output_md = tmp_path / "baseline.md"
    monkeypatch.setattr(updater, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        updater,
        "_parse_args",
        lambda: SimpleNamespace(
            rebind_current_tree=True,
            local_manifest=None,
            source_commit=None,
            source_run_id=None,
            source_run_url=None,
            source_branch="main",
            source_event="push",
            coverage_percent=None,
            coverage_xml=updater.CANONICAL_COVERAGE_XML,
            coverage_log=None,
            slowest_json=updater.CANONICAL_SLOWEST_TESTS_JSON,
            junit=[],
            coverage_threshold=None,
            output_yaml=baseline_path,
            output_md=output_md,
        ),
    )
    monkeypatch.setattr(
        "scripts.engineering.common.repo_paths.resolve_output_path", Path
    )
    monkeypatch.setattr(provenance, "source_commit_is_reachable", lambda *_: True)
    monkeypatch.setattr(subprocess, "check_output", lambda *_args, **_kwargs: "b" * 40)

    with pytest.raises(ValueError, match=message):
        updater.main()
    assert not output_md.exists()


def test_rebind_preserves_measured_identity_and_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "source_event": "local_coverage_verify",
        "source_commit": "a" * 40,
        "source_run_id": "local-capture",
        "source_tree_sha256": "previous-audited-tree",
        "measurement_provenance": {
            "head": "a" * 40,
            "test_tree_sha256": "captured-tree",
            "manifest_sha256": "captured-manifest",
        },
        "coverage": {"actual_percent": 99.0},
        "duration_telemetry": {"total_cases": 17},
    }
    receipt = {
        "schema_version": 1,
        "source_commit": payload["source_commit"],
        "source_run_id": payload["source_run_id"],
        "source_tree_sha256": "captured-tree",
        "manifest_sha256": "captured-manifest",
        "metrics_sha256": provenance.telemetry_metrics_sha256(payload),
    }
    receipt_path = tmp_path / provenance.RECEIPT
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    baseline_path = tmp_path / "baseline.yaml"
    baseline_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    captured = {}
    monkeypatch.setattr(updater, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        updater,
        "_parse_args",
        lambda: SimpleNamespace(
            rebind_current_tree=True,
            local_manifest=None,
            source_commit=None,
            source_run_id=None,
            source_run_url=None,
            source_branch="main",
            source_event="push",
            coverage_percent=None,
            coverage_xml=updater.CANONICAL_COVERAGE_XML,
            coverage_log=None,
            slowest_json=updater.CANONICAL_SLOWEST_TESTS_JSON,
            junit=[],
            coverage_threshold=None,
            output_yaml=baseline_path,
            output_md=tmp_path / "baseline.md",
        ),
    )
    monkeypatch.setattr(
        "scripts.engineering.common.repo_paths.resolve_output_path", Path
    )
    monkeypatch.setattr(provenance, "source_commit_is_reachable", lambda *_: True)
    monkeypatch.setattr(subprocess, "check_output", lambda *_args, **_kwargs: "b" * 40)
    monkeypatch.setattr(
        updater, "compute_test_telemetry_source_tree_sha256", lambda: "current-tree"
    )
    monkeypatch.setattr(
        updater,
        "write_baseline_outputs",
        lambda **kwargs: captured.update(copy.deepcopy(kwargs["payload"])),
    )

    assert updater.main() == 0
    assert captured["source_tree_sha256"] == "current-tree"
    for field in (
        "source_commit",
        "source_run_id",
        "measurement_provenance",
        "coverage",
        "duration_telemetry",
    ):
        assert captured[field] == payload[field]
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
