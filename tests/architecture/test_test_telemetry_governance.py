"""Architecture guards for test-telemetry baseline governance."""

from __future__ import annotations

from pathlib import Path

import yaml


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_committed_test_telemetry_baseline_is_populated() -> None:
    payload = yaml.safe_load(
        Path("configs/quality/test_telemetry_baseline.yaml").read_text(encoding="utf-8")
    )

    assert payload["refresh_status"] == "captured"
    assert payload["source_commit"], "Committed baseline must pin a source commit"
    assert payload["source_run_id"], "Committed baseline must pin a source run id"
    assert payload["coverage"]["actual_percent"] is not None, (
        "Committed baseline must preserve current coverage telemetry"
    )
    assert payload["duration_telemetry"]["total_cases"] is not None, (
        "Committed baseline must preserve current duration telemetry"
    )


def test_testing_docs_distinguish_authoritative_baseline_from_historical_rollup() -> (
    None
):
    testing_guide = _read("docs/03-guides/testing.md")
    qa_readme = _read("scripts/engineering/qa/README.md")
    baseline_doc = _read("docs/05-engineering/test-telemetry-baseline.md")

    assert "`coverage-verify`" in testing_guide
    assert "historical evidence only" in testing_guide
    assert "Current Authoritative Baseline" in baseline_doc
    assert "historical `test-health` rollups remain non-blocking" in baseline_doc
    assert "historical lane history" in qa_readme


def test_slow_governance_cache_probe_is_captured_and_isolated() -> None:
    payload = yaml.safe_load(
        Path("configs/quality/test_telemetry_baseline.yaml").read_text(encoding="utf-8")
    )
    probe = payload["slow_governance_cache_probe"]
    report_probe = probe["probes"][0]

    assert probe["issue_ref"] == "#4663"
    assert probe["source"] == "local_direct_probe"
    assert report_probe["name"] == "collect_test_governance_report"
    assert float(report_probe["first_duration_s"]) > float(
        report_probe["second_duration_s"]
    )
    assert float(report_probe["improvement_factor"]) > 1.0
    assert probe["lane_isolation"] == {
        "fast_boundary_suite_name": "architecture-fast-boundary",
        "slow_governance_suite_name": "architecture-slow-governance",
        "isolated": True,
    }
    assert probe["subprocess_cache"]["entrypoints"] == [
        "tests.architecture.conftest.cached_subprocess_run",
        "tests.architecture.conftest._run_cached_subprocess",
    ]
