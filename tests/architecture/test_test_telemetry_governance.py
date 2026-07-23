"""Architecture guards for test-telemetry baseline governance."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pathlib import Path

import json
import yaml
from scripts.engineering.ci.update_test_telemetry_baseline import (
    compute_test_telemetry_source_tree_sha256,
)


pytestmark = pytest.mark.architecture
REFERENCE_NOW = datetime(2026, 7, 6, tzinfo=UTC)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_committed_test_telemetry_baseline_is_populated() -> None:
    payload = yaml.safe_load(
        Path("configs/quality/test_telemetry_baseline.yaml").read_text(encoding="utf-8")
    )

    assert payload["refresh_status"] == "captured"
    assert payload["source_commit"], "Committed baseline must pin a source commit"
    assert payload["source_run_id"], "Committed baseline must pin a source run id"
    assert payload["source_tree_sha256"] == compute_test_telemetry_source_tree_sha256()
    assert payload["coverage"]["actual_percent"] is not None, (
        "Committed baseline must preserve current coverage telemetry"
    )
    assert payload["duration_telemetry"]["total_cases"] is not None, (
        "Committed baseline must preserve current duration telemetry"
    )
    assert payload["duration_telemetry"]["top_slowest_zones"], (
        "Committed baseline must expose summarized slow zones for branch review"
    )
    context = payload["duration_telemetry"]["execution_context"]
    assert context["executed_count"] == payload["duration_telemetry"]["total_cases"]
    assert context["junit_source_count"] == len(context["junit_sources"])
    assert context["worker_mode"]
    assert context["junit_testcase_duration_sum_s"]
    assert context["explicit_exclusions"]


def test_committed_test_telemetry_baseline_respects_freshness_guard() -> None:
    payload = yaml.safe_load(
        Path("configs/quality/test_telemetry_baseline.yaml").read_text(encoding="utf-8")
    )
    refreshed_at = datetime.fromisoformat(payload["refreshed_at_utc"])
    age = REFERENCE_NOW - refreshed_at

    assert age.days <= int(payload["freshness_guard"]["max_age_days"]), (
        "Committed telemetry baseline is stale. Refresh with "
        "python scripts/engineering/ci/update_test_telemetry_baseline.py"
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


def test_branch_consumable_test_telemetry_reports_match_committed_baseline() -> None:
    payload = yaml.safe_load(
        Path("configs/quality/test_telemetry_baseline.yaml").read_text(encoding="utf-8")
    )
    slowest = json.loads(
        Path("reports/test-telemetry/slowest-tests.json").read_text(encoding="utf-8")
    )
    coverage = json.loads(
        Path("reports/test-telemetry/coverage-summary.json").read_text(encoding="utf-8")
    )
    slowest_md = Path("reports/test-telemetry/slowest-tests.md").read_text(
        encoding="utf-8"
    )

    assert slowest["source_commit"] == payload["source_commit"]
    assert slowest["source_run_id"] == payload["source_run_id"]
    assert slowest["total_cases"] == payload["duration_telemetry"]["total_cases"]
    assert slowest["top_slowest"] == payload["duration_telemetry"]["top_slowest"]
    assert (
        slowest["execution_context"]
        == payload["duration_telemetry"]["execution_context"]
    )
    assert (
        slowest["top_slowest_zones"]
        == payload["duration_telemetry"]["top_slowest_zones"]
    )
    assert coverage["source_commit"] == payload["source_commit"]
    assert coverage["source_run_id"] == payload["source_run_id"]
    assert coverage["coverage"] == payload["coverage"]
    assert "Slowest Tests" in slowest_md
    assert "Top Slow Zones" in slowest_md


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


def _module_path_from_telemetry_node(node_id: str) -> Path | None:
    """Resolve a telemetry node id to a tracked tests/*.py module when possible."""
    module = str(node_id).split("::", 1)[0].strip()
    if not module.startswith("tests."):
        return None
    parts = module.split(".")
    while parts and parts[-1][:1].isupper():
        parts.pop()
    if not parts:
        return None
    candidate = Path(*parts).with_suffix(".py")
    return candidate if candidate.exists() else None


def test_duration_telemetry_top_list_only_references_existing_test_modules() -> None:
    """Stale rankings must not advertise deleted or renamed test modules."""
    payload = yaml.safe_load(
        Path("configs/quality/test_telemetry_baseline.yaml").read_text(encoding="utf-8")
    )
    top_slowest = payload["duration_telemetry"]["top_slowest"]
    assert top_slowest, "Duration telemetry must publish a top-slowest ranking"

    missing: list[str] = []
    for row in top_slowest:
        node = str(row.get("test", ""))
        if _module_path_from_telemetry_node(node) is None:
            missing.append(node)
    assert not missing, (
        "Duration telemetry top list references missing test modules: "
        + ", ".join(missing[:10])
    )


def test_duration_telemetry_execution_context_accounts_for_lane_exclusions() -> None:
    """Full-suite telemetry must either cover lanes or list explicit exclusions."""
    payload = yaml.safe_load(
        Path("configs/quality/test_telemetry_baseline.yaml").read_text(encoding="utf-8")
    )
    context = payload["duration_telemetry"]["execution_context"]
    exclusions = context["explicit_exclusions"]
    assert isinstance(exclusions, list) and exclusions
    assert context["executed_count"] == payload["duration_telemetry"]["total_cases"]
    assert context["lane_wall_time_s"]
    assert context["junit_testcase_duration_sum_s"]
    exclusion_lanes = {str(item.get("lane", "")) for item in exclusions}
    assert "live-provider-contracts" in exclusion_lanes
    assert "performance" in exclusion_lanes
    assert "manual-e2e" in exclusion_lanes
