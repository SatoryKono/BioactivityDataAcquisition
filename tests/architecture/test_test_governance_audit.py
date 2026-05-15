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
    assert (
        report["duplicate_test_name_occurrences"]
        <= budgets["duplicate_test_name_occurrences_max"]
    )
    assert report["compatibility_test_files"] <= budgets["compatibility_test_file_max"]
    assert report["markerless_test_functions"] <= budgets["markerless_test_functions_max"]
    assert report["uuid4_call_sites"] <= budgets["uuid4_call_sites_max"]
    assert report["date_today_call_sites"] <= budgets["date_today_call_sites_max"]
    assert not report["parse_errors"]


@pytest.mark.architecture
def test_assertless_triage_matches_static_report_categories() -> None:
    payload = _load_yaml(CONFIG_PATH)
    report = collect_test_governance_report(ROOT)
    triage = cast(YamlMap, payload["assertless_triage"])
    categories = cast(YamlMap, triage["categories"])

    configured_counts = {
        category: int(cast(YamlMap, entry)["count"])
        for category, entry in categories.items()
    }
    assert configured_counts == report["assertless_category_counts"]
    assert sum(configured_counts.values()) == report["refined_assertless_tests"]
    assert cast(YamlMap, triage["policy"])["new_no_effect_tests"]


@pytest.mark.architecture
def test_no_weak_no_value_candidates_remain_in_integration_or_e2e() -> None:
    report = collect_test_governance_report(ROOT)

    high_priority_weak = [
        candidate
        for candidate in cast(list[YamlMap], report["assertless_candidates"])
        if candidate["category"] == "weak_no_value"
        and (
            str(candidate["path"]).startswith("tests/integration/")
            or str(candidate["path"]).startswith("tests/e2e/")
        )
    ]

    assert high_priority_weak == []


@pytest.mark.architecture
def test_duplicate_name_triage_tracks_top_generic_names() -> None:
    payload = _load_yaml(CONFIG_PATH)
    report = collect_test_governance_report(ROOT)
    triage = cast(YamlMap, payload["duplicate_name_triage"])

    assert triage["total_duplicate_names"] == report["duplicate_test_names"]
    assert triage["duplicate_occurrences"] == report["duplicate_test_name_occurrences"]
    configured_top = {
        cast(str, entry["name"]): int(cast(int, entry["count"]))
        for entry in cast(list[YamlMap], triage["top_generic_names"])
    }
    report_top = {
        cast(str, entry["name"]): int(cast(int, entry["count"]))
        for entry in report["top_duplicate_test_names"][: len(configured_top)]
    }
    assert configured_top == report_top
    assert cast(YamlMap, triage["fixture_builder_policy"])["consolidate_when"]


@pytest.mark.architecture
def test_compatibility_inventory_covers_every_detected_compatibility_test_file() -> None:
    payload = _load_yaml(CONFIG_PATH)
    report = collect_test_governance_report(ROOT)
    inventory = cast(YamlMap, payload["compatibility_test_inventory"])
    entries = cast(list[YamlMap], inventory["entries"])
    configured_paths = {cast(str, entry["path"]) for entry in entries}

    assert inventory["total_files"] == report["compatibility_test_files"]
    assert configured_paths == set(report["compatibility_files"])
    for entry in entries:
        assert entry["decision"] in {
            "retained_compatibility_contract",
            "retained_governance_guard",
            "retained_public_facade_contract",
            "sunset_review",
        }
        assert cast(str, entry["owner"])
        assert cast(str, entry["protected_surface"])
        assert cast(str, entry["policy_ref"]) == "#4209"
        assert cast(str, entry["review_date"]) >= "2026-05-15"
        assert cast(str, entry["rationale"]).strip()


@pytest.mark.architecture
def test_remediation_closeout_tracks_issues_4200_to_4209_with_live_evidence() -> None:
    payload = _load_yaml(CONFIG_PATH)
    closeout = cast(YamlMap, payload["remediation_closeout"])
    entries = cast(list[YamlMap], closeout["issues"])

    assert closeout["parent_issue"] == "#4200"
    assert {entry["issue"] for entry in entries} == {
        "#4201",
        "#4202",
        "#4203",
        "#4204",
        "#4205",
        "#4206",
        "#4207",
        "#4208",
        "#4209",
    }
    for entry in entries:
        assert entry["decision"] == "closeable"
        assert cast(str, entry["closeout"]).strip()
        for evidence in cast(list[str], entry["evidence"]):
            path = evidence.split("::", maxsplit=1)[0]
            assert (ROOT / path).exists(), (
                f"{entry['issue']} references missing closeout evidence: {evidence}"
            )


@pytest.mark.architecture
def test_file_backed_domain_contract_tests_are_explicitly_classified() -> None:
    payload = _load_yaml(CONFIG_PATH)
    policy = cast(YamlMap, payload["file_backed_domain_contract_tests"])
    entries = cast(list[YamlMap], policy["entries"])

    assert policy["decision"] == "retained_contract_lane_exception"
    assert cast(str, policy["rationale"]).strip()
    assert cast(str, policy["review_date"]) >= "2026-05-15"
    assert {entry["path"] for entry in entries} == {
        "tests/unit/domain/schemas/test_constants_yaml.py",
        "tests/unit/domain/normalization/test_pubchem_constants_yaml.py",
        "tests/unit/domain/hash_policy/test_hash_policy_stability.py",
    }
    for entry in entries:
        assert (ROOT / cast(str, entry["path"])).exists()
        assert entry["target_lane"] == "contracts"
        assert cast(str, entry["contract_surface"]).strip()


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
def test_preflight_reports_lfs_pointer_files_as_strict_reproducibility_blocker(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    fixture_root = repo / "tests" / "fixtures" / "vcr" / "chembl"
    fixture_root.mkdir(parents=True)
    (fixture_root / "pointer.yaml").write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0000000000000000000000000000000000000000000000000000000000000000\n"
        "size 123\n",
        encoding="utf-8",
    )
    telemetry = repo / "docs" / "05-engineering" / "test-telemetry-baseline.md"
    telemetry.parent.mkdir(parents=True)
    telemetry.write_text("Actual coverage: 92.81%\n", encoding="utf-8")

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
        repo,
        runner=fake_git_runner,
        git_lfs_path="/usr/bin/git-lfs",
    )

    blocker_ids = {entry["id"] for entry in report["blockers"]}
    assert "lfs_pointer_files_present" in blocker_ids
    assert report["lfs_pointer_files"]["count"] == 1


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
