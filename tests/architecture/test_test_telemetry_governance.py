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
"""Architecture guards for test-telemetry baseline governance."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from scripts.engineering.ci.update_test_telemetry_baseline import (
    compute_test_telemetry_source_tree_sha256,
)

pytestmark = pytest.mark.architecture

REFRESH_HINT = (
    "Refresh with: python -m scripts.engineering.ci.update_test_telemetry_baseline "
    "--source-commit <sha> --source-run-id <run-id> "
    "(see docs/05-engineering/test-telemetry-baseline.md)"
)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _load_baseline() -> dict:
    return yaml.safe_load(
        Path("configs/quality/test_telemetry_baseline.yaml").read_text(encoding="utf-8")
    )


def _reference_now() -> datetime:
    """Return the fixed reference time, with an optional explicit override."""
    raw = os.environ.get("BIOETL_TELEMETRY_REFERENCE_NOW", "").strip()
    if raw:
        value = datetime.fromisoformat(raw)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return datetime(2026, 8, 5, tzinfo=UTC)


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _is_ancestor(commit: str, head: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, head],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def test_committed_test_telemetry_baseline_is_populated() -> None:
    payload = _load_baseline()

    assert payload["refresh_status"] == "captured"
    assert payload["source_commit"], "Committed baseline must pin a source commit"
    assert payload["source_run_id"], "Committed baseline must pin a source run id"
    live_tree = compute_test_telemetry_source_tree_sha256()
    assert payload["source_tree_sha256"] == live_tree, (
        "Committed telemetry source_tree_sha256 drifted from the audited test tree. "
        f"{REFRESH_HINT}"
    )
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
    payload = _load_baseline()
    refreshed_at = datetime.fromisoformat(payload["refreshed_at_utc"])
    if refreshed_at.tzinfo is None:
        refreshed_at = refreshed_at.replace(tzinfo=UTC)
    now = _reference_now()

    assert refreshed_at <= now, (
        "Committed telemetry refreshed_at_utc is in the future relative to reference "
        f"now={now.isoformat()} refreshed_at={refreshed_at.isoformat()}. {REFRESH_HINT}"
    )
    age = now - refreshed_at
    assert age.total_seconds() >= 0
    assert age.days <= int(payload["freshness_guard"]["max_age_days"]), (
        "Committed telemetry baseline is stale. " + REFRESH_HINT
    )


def test_committed_test_telemetry_branch_accurate_source_identity() -> None:
    """Fail closed when branch-accurate telemetry provenance drifts (#5729)."""
    payload = _load_baseline()
    guard = payload.get("branch_accurate_guard") or {}
    assert guard.get("enforced") is True, (
        "branch_accurate_guard.enforced must remain true for committed telemetry"
    )
    assert guard.get("require_source_tree_match") is True

    head = _git_head()
    source_commit = str(payload["source_commit"])
    assert len(source_commit) == 40, "source_commit must be a full 40-char SHA"
    assert _is_ancestor(source_commit, head) or source_commit == head, (
        f"source_commit {source_commit} is not reachable from HEAD {head}. "
        f"{REFRESH_HINT}"
    )

    live_tree = compute_test_telemetry_source_tree_sha256()
    assert payload["source_tree_sha256"] == live_tree, (
        "Branch-accurate telemetry requires source_tree_sha256 to match the audited "
        f"HEAD test tree. {REFRESH_HINT}"
    )

    # When strict HEAD equality is requested (CI audit / local override), enforce it.
    require_head = guard.get("require_source_commit_equals_head") is True
    env_require = os.environ.get(
        "BIOETL_REQUIRE_TELEMETRY_SOURCE_COMMIT_EQUALS_HEAD", ""
    ).strip() in {"1", "true", "TRUE", "yes"}
    if require_head or env_require:
        assert source_commit == head, (
            "Branch-accurate telemetry requires source_commit == HEAD. "
            f"source_commit={source_commit} HEAD={head}. {REFRESH_HINT}"
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
    assert "branch_accurate" in baseline_doc or "source_tree_sha256" in baseline_doc
    assert "update_test_telemetry_baseline" in baseline_doc


def test_branch_consumable_test_telemetry_reports_match_committed_baseline() -> None:
    payload = _load_baseline()
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
    assert slowest["source_tree_sha256"] == payload["source_tree_sha256"]
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
    assert coverage["source_tree_sha256"] == payload["source_tree_sha256"]
    assert coverage["coverage"] == payload["coverage"]
    assert "Slowest Tests" in slowest_md
    assert "Top Slow Zones" in slowest_md


def test_slow_governance_cache_probe_is_captured_and_isolated() -> None:
    payload = _load_baseline()
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
    payload = _load_baseline()
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
    payload = _load_baseline()
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
