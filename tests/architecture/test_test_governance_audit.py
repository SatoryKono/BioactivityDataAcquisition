"""Architecture checks for the 2026-05-15 test-governance issue pack."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from scripts.engineering.qa.check_test_audit_preflight import (
    collect_test_audit_preflight,
)
from scripts.engineering.qa.report_test_governance_audit import (
    collect_test_governance_report,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "quality" / "test_governance_audit.yaml"
GOLD_REGISTRY_PATH = ROOT / "tests" / "fixtures" / "golden" / "gold" / (
    "schema_registry.v1.json"
)

YamlMap = dict[str, Any]


def _load_yaml(path: Path) -> YamlMap:
    with path.open(encoding="utf-8") as handle:
        return cast(YamlMap, yaml.safe_load(handle))


def _issue_ids(payload: YamlMap) -> set[str]:
    return {
        str(entry["id"])
        for entry in cast(list[YamlMap], payload.get("issues", []))
        if isinstance(entry, dict)
    }


@pytest.mark.architecture
def test_test_governance_audit_registry_tracks_exact_issue_set() -> None:
    payload = _load_yaml(CONFIG_PATH)

    assert payload.get("schema_version") == 1
    assert _issue_ids(payload) == {
        "4159",
        "4161",
        "4163",
        "4165",
        "4167",
        "4169",
        "4172",
        "4174",
        "4176",
    }


@pytest.mark.architecture
def test_test_governance_audit_evidence_paths_exist() -> None:
    payload = _load_yaml(CONFIG_PATH)

    for entry in cast(list[YamlMap], payload.get("issues", [])):
        for relative_path in cast(list[str], entry.get("evidence_paths", [])):
            assert (ROOT / relative_path).exists(), (
                f"Missing governance evidence for issue #{entry['id']}: "
                f"{relative_path}"
            )


@pytest.mark.architecture
def test_static_test_governance_report_stays_within_committed_budgets() -> None:
    payload = _load_yaml(CONFIG_PATH)
    report = collect_test_governance_report(ROOT)
    budgets = cast(YamlMap, payload["budgets"])

    assert report["refined_assertless_tests"] <= budgets["refined_assertless_max"]
    assert report["duplicate_test_names"] <= budgets["duplicate_test_names_max"]
    assert report["compatibility_test_files"] <= budgets["compatibility_test_file_max"]
    assert report["markerless_test_functions"] <= budgets["markerless_test_functions_max"]
    assert report["uuid4_call_sites"] <= budgets["uuid4_call_sites_max"]
    assert report["date_today_call_sites"] <= budgets["date_today_call_sites_max"]
    assert not report["parse_errors"]


@pytest.mark.architecture
def test_preflight_reports_missing_git_lfs_as_strict_reproducibility_blocker() -> None:
    def fake_git_runner(args: list[str]) -> subprocess.CompletedProcess[str]:
        values = {
            ("branch", "--show-current"): "main",
            ("rev-parse", "--short", "HEAD"): "abc1234",
            (
                "symbolic-ref",
                "--quiet",
                "--short",
                "refs/remotes/origin/HEAD",
            ): "origin/main",
            ("rev-parse", "--short", "main"): "abc1234",
            ("status", "--short", "--untracked-files=no"): "",
        }
        key = tuple(args)
        if key in values:
            return subprocess.CompletedProcess(args, 0, values[key], "")
        return subprocess.CompletedProcess(args, 1, "", f"unexpected git args: {args}")

    report = collect_test_audit_preflight(
        ROOT,
        runner=fake_git_runner,
        git_lfs_path="",
    )

    blocker_ids = {entry["id"] for entry in report["blockers"]}
    assert "missing_git_lfs" in blocker_ids
    assert report["default_branch"] == "main"
    assert report["telemetry_baseline"]["exists"] is True


@pytest.mark.architecture
def test_gold_dq_registry_contains_required_governance_bundles() -> None:
    payload = _load_yaml(CONFIG_PATH)
    registry = json.loads(GOLD_REGISTRY_PATH.read_text(encoding="utf-8"))
    dq_outputs = registry["dq_sensitive_outputs"]
    gold_dq = cast(YamlMap, payload["gold_dq"])

    assert len(dq_outputs) >= gold_dq["min_dq_sensitive_outputs"]
    for bundle_name in cast(list[str], gold_dq["required_bundles"]):
        assert bundle_name in dq_outputs
        assert (ROOT / dq_outputs[bundle_name]["snapshot_path"]).exists()


@pytest.mark.architecture
def test_lane_docs_forbid_marker_only_commands_as_canonical_lanes() -> None:
    payload = _load_yaml(CONFIG_PATH)
    docs_path = ROOT / cast(YamlMap, payload["lane_policy"])["docs"]
    text = docs_path.read_text(encoding="utf-8")

    assert "Marker-only commands such as `pytest -m unit` are not canonical lanes" in text


@pytest.mark.architecture
def test_tracing_emission_contract_test_remains_present() -> None:
    payload = _load_yaml(CONFIG_PATH)
    tracing = cast(YamlMap, payload["tracing"])
    test_path = ROOT / tracing["runtime_emission_test"]
    text = test_path.read_text(encoding="utf-8")

    assert "class RecordingTracing" in text
    for test_name in cast(list[str], tracing["required_test_names"]):
        assert f"def {test_name}" in text
