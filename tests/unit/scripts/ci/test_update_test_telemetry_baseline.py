"""Unit tests for test telemetry baseline updater."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.ci.update_test_telemetry_baseline import (
    _read_coverage_percent,
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
        slowest_json_path=slowest_json,
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
