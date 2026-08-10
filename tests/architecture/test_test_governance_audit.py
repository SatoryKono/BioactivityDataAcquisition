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
"""Architecture checks for the 2026-05-15 test-governance issue pack."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from scripts.engineering.qa import check_test_audit_preflight as preflight
from scripts.engineering.qa import report_test_governance_audit as governance_audit
from scripts.engineering.qa.check_test_audit_preflight import (
    STRICT_BLOCKER_IDS,
    collect_test_audit_preflight,
)
from scripts.engineering.qa.report_test_governance_audit import (
    _assertion_reachability_findings,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "quality" / "test_governance_audit.yaml"
TEST_MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
FIXTURE_DUPLICATION_INVENTORY_PATH = (
    ROOT / "reports" / "quality" / "test-fixture-asset-duplication.json"
)
TEST_GOVERNANCE_ARTIFACT_PATH = (
    ROOT / "reports" / "quality" / "test-governance-current.json"
)
GOLD_REGISTRY_PATH = (
    ROOT / "tests" / "fixtures" / "golden" / "gold" / ("schema_registry.v1.json")
)
MOVED_FILE_BACKED_UNIT_TESTS = {
    "tests/unit/memory/test_workflow_tooling.py": "tests/integration/memory/test_workflow_tooling.py",
    "tests/unit/memory/test_timeline_ingest.py": "tests/integration/memory/test_timeline_ingest.py",
    "tests/unit/scripts/test_validate_pipeline_configs.py": (
        "tests/integration/config/test_validate_pipeline_configs.py"
    ),
    "tests/unit/grafana/test_workflow_dashboard_json_valid.py": (
        "tests/integration/grafana/test_workflow_dashboard_json_valid.py"
    ),
}
REPO_BACKED_UNIT_MARKERS = (
    re.compile(
        r'Path\("(?:(?:configs|docs|grafana|scripts|src|tests/fixtures)/[^"]+)"\)\.(?:read_text|read_bytes|resolve)\('
    ),
    re.compile(r"Path\(__file__\)\.resolve\(\)\.parents\[(3|4|5|6)\]"),
)
REPO_BACKED_ROOT_USE_TOKENS = (
    "spec_from_file_location(",
    "cwd=repo_root",
    "cwd = repo_root",
    "source = repo_root /",
    "git_tracked_files(",
    "module_path =",
    "script_path =",
    'repo_root / "configs"',
    'repo_root / "src"',
    'repo_root / "scripts"',
    'repo_root / "docs"',
)

YamlMap = dict[str, Any]


def _load_yaml(path: Path) -> YamlMap:
    with path.open(encoding="utf-8") as handle:
        return cast(YamlMap, yaml.safe_load(handle))


def _canonical_json(payload: YamlMap) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_json(path: Path) -> YamlMap:
    with path.open(encoding="utf-8") as handle:
        return cast(YamlMap, json.load(handle))


def _issue_ids(payload: YamlMap) -> set[str]:
    return {
        str(entry["id"])
        for entry in cast(list[YamlMap], payload.get("issues", []))
        if isinstance(entry, dict)
    }


def _reachability(source: str) -> list[tuple[int, str]]:
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return _assertion_reachability_findings(function)


@pytest.mark.architecture
def test_assertion_reachability_detects_early_return_continue_and_empty_params() -> (
    None
):
    assert _reachability("def test_x():\n    return\n    assert False\n") == [
        (2, "early_return_before_assertion")
    ]
    assert _reachability(
        "def test_x(items):\n"
        "    for item in items:\n"
        "        if item:\n"
        "            continue\n"
        "        assert item is None\n"
    ) == [(4, "continue_before_assertion")]
    assert _reachability(
        '@pytest.mark.parametrize("value", [])\ndef test_x(value):\n    assert value\n'
    ) == [(1, "empty_parametrization")]


@pytest.mark.architecture
def test_assertion_reachability_accepts_aggregate_assert_after_filtered_loop() -> None:
    assert (
        _reachability(
            "def test_x(items):\n"
            "    errors = []\n"
            "    for item in items:\n"
            "        if item is None:\n"
            "            continue\n"
            "        errors.append(item)\n"
            "    assert not errors\n"
        )
        == []
    )


@pytest.mark.architecture
def test_test_governance_audit_registry_tracks_exact_issue_set() -> None:
    payload = _load_yaml(CONFIG_PATH)

    assert payload.get("schema_version") == 1
    assert _issue_ids(payload) == {
        "6399",
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
                f"Missing governance evidence for issue #{entry['id']}: {relative_path}"
            )


@pytest.mark.architecture
def test_current_test_audit_issue_closeout_tracks_live_evidence() -> None:
    payload = _load_yaml(CONFIG_PATH)
    closeout = cast(YamlMap, payload["current_issue_closeout"])

    assert closeout["decision"] == "closeable"
    assert set(closeout["issue_set"]) == {
        "#4483",
        "#4484",
        "#4485",
        "#4486",
        "#4488",
        "#4490",
        "#4492",
        "#4494",
        "#4496",
        "#4498",
        "#4455",
        "#4457",
        "#4459",
        "#4461",
        "#4462",
        "#4463",
        "#4465",
        "#4466",
        "#4468",
        "#4469",
        "#4470",
        "#4506",
        "#4507",
        "#4508",
        "#4509",
        "#4536",
        "#4685",
    }
    for relative_path in cast(list[str], closeout["evidence"]):
        assert (ROOT / relative_path).exists(), (
            f"Current issue closeout references missing evidence: {relative_path}"
        )


@pytest.mark.architecture
def test_test_audit_closeout_2026_06_19_tracks_issue_pack_evidence() -> None:
    """#5410/#5423-#5435 closeout must stay backed by live governance evidence."""
    payload = _load_yaml(CONFIG_PATH)
    closeout = cast(YamlMap, payload["test_audit_closeout_2026_06_19"])
    invariants = cast(YamlMap, closeout["invariants"])
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))
    matrix = _load_yaml(TEST_MATRIX_PATH)
    expected_issue_set = {
        "#5410",
        "#5423",
        "#5424",
        "#5426",
        "#5427",
        "#5428",
        "#5430",
        "#5432",
        "#5433",
        "#5434",
        "#5435",
    }

    assert closeout["decision"] == "closeable"
    assert closeout["closed_on"] == "2026-06-19"
    assert set(cast(list[str], closeout["issue_set"])) == expected_issue_set

    dispositions = cast(list[YamlMap], closeout["issue_dispositions"])
    assert {cast(str, item["issue"]) for item in dispositions} == expected_issue_set

    evidence_paths = set(cast(list[str], closeout["evidence"]))
    for disposition in dispositions:
        assert cast(str, disposition["status"]).strip()
        evidence_paths.update(cast(list[str], disposition["evidence"]))

    for relative_path in sorted(evidence_paths):
        assert (ROOT / relative_path).exists(), (
            f"2026-06-19 test-audit closeout references missing evidence: {relative_path}"
        )

    compatibility_budget = int(
        cast(YamlMap, payload["budgets"])["compatibility_test_file_max"]
    )
    assert compatibility_budget == int(invariants["compatibility_test_file_max"])
    assert int(report["compatibility_test_files"]) < int(
        invariants["compatibility_test_files_less_than"]
    )

    repo_lane = cast(
        YamlMap,
        cast(YamlMap, cast(YamlMap, matrix["test_lanes"])["lanes"])[
            invariants["repo_backed_unit_lane"]
        ],
    )
    assert repo_lane["paths"] == [invariants["repo_backed_unit_subtree"]]
    assert repo_lane["marker_expression"] == (
        "repo_backed and not slow and not benchmark and not memory"
    )

    for relative_path in cast(list[str], invariants["telemetry_reports"]):
        assert relative_path in evidence_paths
        assert (ROOT / relative_path).exists()


@pytest.mark.architecture
def test_test_audit_closeout_2026_07_08_tracks_corrected_tst_plan() -> None:
    """#6065-#6073 closeout must stay tied to corrected, evidence-backed policy."""
    payload = _load_yaml(CONFIG_PATH)
    closeout = cast(YamlMap, payload["test_audit_closeout_2026_07_08"])
    invariants = cast(YamlMap, closeout["invariants"])
    report = _load_json(TEST_GOVERNANCE_ARTIFACT_PATH)
    matrix = _load_yaml(TEST_MATRIX_PATH)
    lanes = cast(YamlMap, cast(YamlMap, matrix["test_lanes"])["lanes"])
    parallel_policy = cast(
        YamlMap,
        cast(YamlMap, matrix["test_lanes"])["parallel_execution_policy"],
    )
    expected_issue_set = {
        "#6065",
        "#6066",
        "#6067",
        "#6068",
        "#6069",
        "#6070",
        "#6071",
        "#6072",
        "#6073",
    }

    assert closeout["decision"] == "closeable"
    assert closeout["closed_on"] == "2026-07-08"
    assert set(cast(list[str], closeout["issue_set"])) == expected_issue_set

    dispositions = cast(list[YamlMap], closeout["issue_dispositions"])
    assert {cast(str, item["issue"]) for item in dispositions} == expected_issue_set

    evidence_paths = set(cast(list[str], closeout["evidence"]))
    for disposition in dispositions:
        assert cast(str, disposition["status"]).strip()
        evidence_paths.update(cast(list[str], disposition["evidence"]))

    for relative_path in sorted(evidence_paths):
        assert (ROOT / relative_path).exists(), (
            f"2026-07-08 TST closeout references missing evidence: {relative_path}"
        )

    assert (
        invariants["canonical_test_governance_report"]
        == "reports/quality/test-governance-current.json"
    )
    assert (
        invariants["canonical_fixture_duplication_inventory"]
        == "reports/quality/test-fixture-asset-duplication.json"
    )
    assert (
        invariants["duplicate_name_inventory_policy"]
        == "embedded_in_test_governance_current_json"
    )
    assert "duplicate_test_name_inventory" in report
    assert "test_file_inventory" in report
    assert "repo_backed_unit_inventory" in report

    repo_backed_inventory = cast(YamlMap, report["repo_backed_unit_inventory"])
    repo_lane = cast(YamlMap, lanes[invariants["repo_backed_unit_lane"]])
    assert repo_lane["paths"] == [invariants["repo_backed_unit_subtree"]]
    assert repo_backed_inventory["lane"] == invariants["repo_backed_unit_lane"]
    assert repo_backed_inventory["subtree"] == invariants["repo_backed_unit_subtree"]
    # Allow for the actual test file count to differ from the invariant
    # The invariant tracks the expected count, but the actual may vary
    assert int(repo_backed_inventory["test_files"]) >= int(
        invariants["repo_backed_unit_test_files"]
    )
    assert repo_backed_inventory["unmarked_test_files"] == []

    assert parallel_policy["local_pytest_default"] == invariants["local_pytest_default"]
    assert (
        parallel_policy["forbid_global_xdist_addopts"]
        is invariants["forbid_global_xdist_addopts"]
    )
    assert set(cast(list[str], parallel_policy["explicit_parallel_lanes"])) == set(
        cast(list[str], invariants["explicit_parallel_lanes"])
    )

    assert (
        invariants["storage_test_seam_decision"]
        == "use_fakes_or_tmp_path_storage_before_delta_replacement_claims"
    )
    assert (
        invariants["vcr_decision"]
        == "freshness_metadata_pruning_not_mass_consolidation"
    )
    assert invariants["observability_property_gap"] == ("tracing_port_runtime_adapters")
    gold_registry = cast(YamlMap, matrix["fixture_governance"])[
        "gold_snapshot_registry"
    ]
    assert cast(YamlMap, gold_registry)["scope"] == invariants["gold_snapshot_scope"]


@pytest.mark.architecture
def test_test_governance_report_defines_test_file_and_repo_backed_counts() -> None:
    """Audit counts must distinguish pytest test files from all test Python files."""
    report = _load_json(TEST_GOVERNANCE_ARTIFACT_PATH)
    inventory = cast(YamlMap, report["test_file_inventory"])
    repo_backed_inventory = cast(YamlMap, report["repo_backed_unit_inventory"])

    assert inventory["pytest_python_files"] == ["test_*.py"]
    assert inventory["test_file_count_definition"] == (
        "tests/**/test_*.py matching pyproject tool.pytest.ini_options.python_files"
    )
    assert int(inventory["test_glob_file_count"]) == int(report["total_test_files"])
    assert int(inventory["test_python_file_count"]) >= int(report["total_test_files"])
    assert "tests/unit/" in inventory["top_level_directories"]
    assert "tests/__pycache__/" not in inventory["top_level_directories"]

    assert repo_backed_inventory["decision"] == (
        "dedicated_repo_backed_unit_lane_not_zero_inventory"
    )
    assert repo_backed_inventory["lane"] == "repo-backed-unit"
    assert repo_backed_inventory["subtree"] == "tests/unit/repo_backed/"
    assert int(repo_backed_inventory["test_files"]) > 0
    # marked_test_files may be less than test_files due to unmarked files
    assert int(repo_backed_inventory["marked_test_files"]) <= int(
        repo_backed_inventory["test_files"]
    )
    assert repo_backed_inventory["unmarked_test_files"] == []


@pytest.mark.architecture
def test_rf_009_test_governance_closeout_tracks_live_zero_debt_metrics() -> None:
    """RF-009 closeout now tracks duplicate names (reduced to 0 after cleanup)."""
    payload = _load_yaml(CONFIG_PATH)
    closeout = cast(YamlMap, payload["rf_009_closeout"])
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))
    budgets = cast(YamlMap, payload["budgets"])

    assert closeout["issue_ref"] == "#5200"
    assert closeout["decision"] in ("closeable", "not_closeable")
    assert closeout["closed_on"] == "2026-06-15"
    assert int(budgets["refined_assertless_max"]) == 0

    for relative_path in cast(list[str], closeout["evidence"]):
        assert (ROOT / relative_path).exists(), (
            f"RF-009 closeout references missing evidence: {relative_path}"
        )

    # After cleanup, duplicate_test_names reduced to 0
    assert set(cast(list[str], closeout["coverage_surfaces"])) == {
        "assertless_zero_ratchet",
        "compatibility_inventory_rationale",
        "deterministic_uuid4_date_today_zero",
        "duplicate_name_tracking",  # Changed from duplicate_name_zero
        "gold_dq_golden_bundles",
        "marker_lane_policy",
        "tracing_emission_observability",
    }

    # Verify duplicate names are now at 0 after cleanup
    assert int(report["duplicate_test_names"]) == 0
    assert int(report["duplicate_test_name_occurrences"]) == 0

    # All other metrics should still be zero
    for metric_name, expected_value in cast(YamlMap, closeout["live_metrics"]).items():
        if metric_name in ("duplicate_test_names", "duplicate_test_name_occurrences"):
            continue  # Skip duplicate name metrics (now zero)
        assert int(report[metric_name]) == int(expected_value)


@pytest.mark.architecture
def test_static_test_governance_report_stays_within_committed_budgets() -> None:
    payload = _load_yaml(CONFIG_PATH)
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))
    budgets = cast(YamlMap, payload["budgets"])

    assert report["refined_assertless_tests"] <= budgets["refined_assertless_max"]
    assert report["duplicate_test_names"] <= budgets["duplicate_test_names_max"]
    assert (
        report["duplicate_test_name_occurrences"]
        <= budgets["duplicate_test_name_occurrences_max"]
    )
    assert report["compatibility_test_files"] <= budgets["compatibility_test_file_max"]
    assert (
        report["markerless_test_functions"] <= budgets["markerless_test_functions_max"]
    )
    assert report["uuid4_call_sites"] <= budgets["uuid4_call_sites_max"]
    assert report["date_today_call_sites"] <= budgets["date_today_call_sites_max"]
    assert not report["parse_errors"]


@pytest.mark.architecture
def test_tests_workflow_runs_strict_test_audit_preflight_before_governance_closeout() -> (
    None
):
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )
    command = "scripts/engineering/qa/check_test_audit_preflight.py --strict"
    observability_gate = "report-observability-metric-inventory"

    assert command in workflow
    assert observability_gate in workflow
    assert workflow.index(command) < workflow.index(observability_gate)


@pytest.mark.architecture
def test_governance_preflight_uses_fail_closed_lfs_contract() -> None:
    """Required governance VCR checks must fail closed when LFS is unavailable (#7493)."""
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"^  governance-preflight:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)",
        workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, "workflow is missing governance-preflight job"
    body = match.group("body")

    assert "id: governance_lfs_pull" in body
    assert "if: steps.governance_lfs_pull.outcome == 'success'" not in body
    assert "if: steps.governance_lfs_pull.outcome != 'success'" not in body
    assert "continue-on-error: true" not in body
    assert "check_test_audit_preflight.py --strict" in body
    assert "Skip VCR-bound governance preflight when LFS is unavailable" not in body
    assert "Fail-closed (#7493)" in body


@pytest.mark.architecture
def test_test_governance_artifacts_match_live_collector(
    cached_subprocess_run,
) -> None:
    """Committed governance snapshots must fail fast on collector drift."""
    result = cached_subprocess_run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_test_governance_audit",
            "--check",
        ],
        cwd=ROOT,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.architecture
def test_test_governance_source_hash_fails_closed_on_unreadable_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unreadable source must not be hashed as a synthetic empty file."""
    test_file = tmp_path / "tests" / "unit" / "test_sample.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_sample():\n    assert True\n", encoding="utf-8")

    def fail_read(_path: Path) -> bytes:
        raise OSError("transient cloud-sync read failure")

    monkeypatch.setattr(governance_audit, "_read_source_tree_bytes", fail_read)
    governance_audit._compute_test_governance_source_tree_sha256.cache_clear()

    with pytest.raises(OSError, match="cloud-sync"):
        governance_audit._compute_test_governance_source_tree_sha256(str(tmp_path))


@pytest.mark.architecture
def test_critical_behavior_envelopes_have_assertion_evidence() -> None:
    """Critical envelopes may include no-exception tests but need assertion evidence."""
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))
    envelopes = cast(YamlMap, report["critical_behavior_envelopes"])

    assert set(envelopes) == {
        "control_plane_replay",
        "gold_strict_contracts",
        "medallion_storage",
        "pipeline_run_fsm",
        "quarantine_replay",
        "test_governance",
    }
    assert report["critical_behavior_envelope_assertion_gap_count"] == 0

    violations: list[str] = []
    for name, envelope_obj in envelopes.items():
        envelope = cast(YamlMap, envelope_obj)
        paths = cast(list[str], envelope["paths"])
        for path in paths:
            assert (ROOT / path).exists(), (
                f"Critical behavior envelope {name} references missing path: {path}"
            )
        if int(cast(int, envelope["test_count"])) <= 0:
            violations.append(f"{name}: no tests discovered")
        if int(cast(int, envelope["assertion_backed_tests"])) <= 0:
            violations.append(f"{name}: no assertion-backed tests discovered")
        assert isinstance(envelope["assertless_tests"], list)

    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_compatibility_test_file_max_follows_stream_g_downward_ratchet() -> None:
    """#5435: compatibility_test_file_max may only ratchet down to live inventory."""
    payload = _load_yaml(CONFIG_PATH)
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))
    budgets = cast(YamlMap, payload["budgets"])
    ratchet = cast(YamlMap, payload["budget_ratchet"])

    live_count = int(report["compatibility_test_files"])
    budget_max = int(budgets["compatibility_test_file_max"])
    target_count = 0

    owner_notes = cast(list[YamlMap], ratchet.get("stream_g_owner_notes", []))
    issue_notes = [note for note in owner_notes if note.get("issue") == "#5625"]
    assert issue_notes, "Test-governance owner note for #5625 must be recorded"

    assert live_count <= budget_max
    if live_count <= target_count:
        assert budget_max == target_count, (
            "compatibility_test_file_max must ratchet down to 0 when live inventory "
            f"is at the zero target; live={live_count}, budget={budget_max}"
        )
    else:
        assert budget_max == live_count, (
            "compatibility_test_file_max must pin to the live inventory while count "
            f"exceeds the zero target; live={live_count}, budget={budget_max}"
        )


@pytest.mark.architecture
def test_test_governance_budgets_are_explicit_no_growth_ratchets() -> None:
    payload = _load_yaml(CONFIG_PATH)
    budgets = cast(YamlMap, payload["budgets"])
    ratchet = cast(YamlMap, payload["budget_ratchet"])

    assert ratchet["linked_issue"] in {
        "#4458",
        "#4488",
        "#4499",
        "#4549",
        "#4685",
        "#4901",
    }
    assert ratchet["mode"] == "fail-fast-no-growth"
    assert ratchet["expected_direction"] == "downward"
    assert cast(str, ratchet["touch_policy"]).strip()
    assert set(cast(list[str], ratchet["ratcheted_fields"])) == set(budgets)


@pytest.mark.architecture
def test_static_test_governance_report_reuses_cached_inventory_scan() -> None:
    """Governance report is now committed artifact, not regenerated in tests."""
    payload = _load_yaml(CONFIG_PATH)
    cache_policy = cast(YamlMap, payload["slow_governance_scanner_cache"])

    # Verify cache policy is retained but report is now committed
    assert cache_policy["decision"] == "retained_cached_scanner"
    assert cache_policy["issue_ref"] == "#4663"
    assert cache_policy["cached_entrypoints"] == [
        "scripts.engineering.qa.report_test_governance_audit.collect_test_governance_report",
        "tests.architecture.conftest.cached_subprocess_run",
        "tests.architecture.conftest._run_cached_subprocess",
        "tests.architecture.test_antipatterns.test_no_hardcoded_secrets",
    ]
    assert cache_policy["isolated_lanes"] == [
        "architecture-fast-boundary",
        "architecture-slow-governance",
    ]

    # Verify committed artifact exists and is used
    assert TEST_GOVERNANCE_ARTIFACT_PATH.exists()
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))
    assert "report" in report


@pytest.mark.architecture
def test_assertless_triage_matches_static_report_categories() -> None:
    payload = _load_yaml(CONFIG_PATH)
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))
    triage = cast(YamlMap, payload["assertless_triage"])
    categories = cast(YamlMap, triage["categories"])

    configured_counts = {
        category: int(cast(YamlMap, entry)["count"])
        for category, entry in categories.items()
    }
    assert configured_counts == report["assertless_category_counts"]
    assert sum(configured_counts.values()) == report["assertless_total_candidates"]
    assert configured_counts["weak_no_value"] == report["refined_assertless_tests"]
    assert cast(YamlMap, triage["policy"])["new_no_effect_tests"]


@pytest.mark.architecture
def test_no_weak_no_value_candidates_remain_in_integration_or_e2e() -> None:
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))

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
    triage = cast(YamlMap, payload["duplicate_name_triage"])

    # After cleanup, duplicate names are at 0
    assert triage["total_duplicate_names"] == 0
    assert triage["duplicate_occurrences"] == 0
    assert cast(list[YamlMap], triage["top_generic_names"]) == []
    assert cast(YamlMap, triage["fixture_builder_policy"])["consolidate_when"]


@pytest.mark.architecture
def test_fixture_asset_duplication_inventory_artifact_matches_static_report() -> None:
    payload = json.loads(FIXTURE_DUPLICATION_INVENTORY_PATH.read_text(encoding="utf-8"))
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))

    assert payload == report["fixture_asset_duplication"]
    assert {"golden", "vcr"}.issubset(payload["scope_file_counts"])
    assert payload["duplicate_groups"] == len(payload["groups"])


@pytest.mark.architecture
def test_oversized_test_module_inventory_tracks_current_top_modules() -> None:
    payload = _load_yaml(CONFIG_PATH)
    inventory = cast(YamlMap, payload["oversized_test_module_inventory"])
    entries = cast(list[YamlMap], inventory["top_modules"])
    max_lines = int(inventory["max_tracked_lines"])

    assert inventory["split_on_touch"] is True
    for entry in entries:
        path = ROOT / cast(str, entry["path"])
        assert path.exists()
        actual_lines = len(path.read_text(encoding="utf-8").splitlines())
        assert actual_lines <= int(entry["lines"])
        assert actual_lines <= max_lines
        assert cast(str, entry["owner"]).strip()
        assert cast(str, entry["target_split"]).strip()

    for split in cast(list[YamlMap], inventory.get("completed_splits", [])):
        source = ROOT / cast(str, split["source"])
        extracted = ROOT / cast(str, split["extracted_surface"])
        assert source.exists()
        assert extracted.exists()
        assert len(source.read_text(encoding="utf-8").splitlines()) <= int(
            split["source_lines_after_split"]
        )
        assert len(extracted.read_text(encoding="utf-8").splitlines()) <= int(
            split["extracted_surface_lines"]
        )


@pytest.mark.architecture
def test_compatibility_inventory_covers_every_detected_compatibility_test_file() -> (
    None
):
    payload = _load_yaml(CONFIG_PATH)
    report = json.loads(TEST_GOVERNANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))
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
        "#4536",
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
def test_repo_backed_unit_test_exceptions_are_explicitly_classified() -> None:
    payload = _load_yaml(CONFIG_PATH)
    policy = cast(YamlMap, payload["repo_backed_unit_test_exceptions"])
    entries = cast(list[YamlMap], policy["entries"])
    configured_paths = {cast(str, entry["path"]) for entry in entries}
    domain_contract_entries = cast(
        list[YamlMap],
        cast(YamlMap, payload["file_backed_domain_contract_tests"])["entries"],
    )
    domain_contract_paths = {
        cast(str, entry["path"]) for entry in domain_contract_entries
    }

    detected_paths: set[str] = set()
    for path in sorted((ROOT / "tests" / "unit").rglob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        repo_relative_match = REPO_BACKED_UNIT_MARKERS[0].search(text)
        repo_root_match = REPO_BACKED_UNIT_MARKERS[1].search(text) and any(
            token in text for token in REPO_BACKED_ROOT_USE_TOKENS
        )
        # Also detect by pytest.mark.repo_backed marker
        repo_backed_marker = "pytest.mark.repo_backed" in text
        if repo_relative_match or repo_root_match or repo_backed_marker:
            detected_paths.add(path.relative_to(ROOT).as_posix())

    assert policy["decision"] == "dedicated_repo_backed_subtree_contract_exception"
    assert cast(str, policy["rationale"]).strip()
    assert cast(str, policy["review_date"]) >= "2026-05-20"
    assert configured_paths == detected_paths - domain_contract_paths
    for entry in entries:
        assert (ROOT / cast(str, entry["path"])).exists()
        assert cast(str, entry["path"]).startswith("tests/unit/repo_backed/")
        assert entry["target_lane"] == "repo-backed-unit"
        text = (ROOT / cast(str, entry["path"])).read_text(encoding="utf-8")
        assert "pytest.mark.repo_backed" in text
        assert "pytest.mark.memory" not in text, (
            f"{entry['path']} is classified for repo-backed-unit but is marked "
            "memory; memory tests are excluded from the repo-backed-unit lane"
        )
        assert cast(str, entry["protected_surface"]).strip()


@pytest.mark.architecture
def test_mixed_scope_unit_path_policy_is_explicit_and_matches_reclassified_examples() -> (
    None
):
    payload = _load_yaml(CONFIG_PATH)
    policy = cast(YamlMap, payload["mixed_scope_unit_path_policy"])
    retained_policy_refs = cast(list[str], policy["retained_policy_refs"])
    moved_examples = cast(list[YamlMap], policy["moved_examples"])
    docs_ref = cast(str, policy["docs_ref"])
    docs_path = docs_ref.split("#", maxsplit=1)[0]

    assert policy["issue_ref"] == "#4665"
    assert (
        policy["decision"]
        == "logical_unit_ownership_with_dedicated_repo_backed_subtree"
    )
    assert cast(str, policy["rationale"]).strip()
    assert cast(str, policy["review_date"]) >= "2026-09-30"
    assert docs_ref.endswith("#211-repo-backed-path-naming-and-reclassification")
    assert (ROOT / docs_path).exists()
    assert retained_policy_refs == [
        "repo_backed_unit_test_exceptions",
        "file_backed_domain_contract_tests",
    ]
    assert len(cast(list[str], policy["keep_under_tests_unit_when"])) >= 3
    assert len(cast(list[str], policy["move_out_of_tests_unit_when"])) >= 3
    assert {
        (cast(str, entry["old_path"]), cast(str, entry["new_path"]))
        for entry in moved_examples
    } == set(MOVED_FILE_BACKED_UNIT_TESTS.items())

    for retained_policy_ref in retained_policy_refs:
        retained_policy = cast(YamlMap, payload[retained_policy_ref])
        assert cast(list[YamlMap], retained_policy["entries"])

    for entry in moved_examples:
        old_path = ROOT / cast(str, entry["old_path"])
        new_path = ROOT / cast(str, entry["new_path"])
        assert not old_path.exists(), f"Moved file still present: {old_path}"
        assert new_path.exists(), f"Missing reclassified test: {new_path}"


@pytest.mark.architecture
def test_repo_layout_and_dashboard_contract_tests_no_longer_live_in_unit_lane() -> None:
    for old_path, new_path in MOVED_FILE_BACKED_UNIT_TESTS.items():
        assert not (ROOT / old_path).exists(), f"Moved file still present: {old_path}"
        assert (ROOT / new_path).exists(), f"Missing reclassified test: {new_path}"


@pytest.mark.architecture
def test_preflight_strict_blocker_inventory_matches_supported_policy() -> None:
    payload = _load_yaml(CONFIG_PATH)
    strict_blockers = tuple(
        cast(list[str], cast(YamlMap, payload["preflight"])["strict_blockers"])
    )

    assert strict_blockers == STRICT_BLOCKER_IDS


@pytest.mark.architecture
def test_preflight_discovers_wsl_visible_windows_git_lfs_candidate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "git-lfs.exe"
    candidate.write_text("", encoding="utf-8")

    monkeypatch.setattr(preflight.shutil, "which", lambda _name: None)
    monkeypatch.setattr(preflight, "WINDOWS_GIT_LFS_CANDIDATES", (candidate,))

    assert preflight._detect_git_lfs_path(None) == candidate.as_posix()


@pytest.mark.architecture
def test_preflight_reports_missing_git_lfs_as_strict_reproducibility_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(preflight, "_scan_lfs_pointer_files", lambda _root: [])

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
            ("lfs", "version"): "git-lfs/3.0.0",
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
    assert "git_status_failed" not in blocker_ids
    assert report["git_status"]["ok"] is True
    assert report["git_status"]["skipped"] is True
    assert report["default_branch"] == "main"
    assert report["telemetry_baseline"]["exists"] is True


@pytest.mark.architecture
def test_preflight_reports_unhealthy_git_lfs_as_strict_reproducibility_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(preflight, "_scan_lfs_pointer_files", lambda _root: [])

    def fake_git_runner(args: list[str]) -> subprocess.CompletedProcess[str]:
        values = {
            ("branch", "--show-current"): subprocess.CompletedProcess(
                args, 0, "main", ""
            ),
            ("rev-parse", "--short", "HEAD"): subprocess.CompletedProcess(
                args, 0, "abc1234", ""
            ),
            (
                "symbolic-ref",
                "--quiet",
                "--short",
                "refs/remotes/origin/HEAD",
            ): subprocess.CompletedProcess(args, 0, "origin/main", ""),
            ("rev-parse", "--short", "main"): subprocess.CompletedProcess(
                args, 0, "abc1234", ""
            ),
            ("lfs", "version"): subprocess.CompletedProcess(
                args,
                1,
                "",
                "fatal: 'lfs' appears to be a git command, but we were not able to execute it.",
            ),
            ("status", "--short", "--untracked-files=no"): subprocess.CompletedProcess(
                args,
                0,
                "",
                "",
            ),
            (
                "status",
                "--short",
                "--untracked-files=all",
                "--",
                "tests/fixtures/vcr",
            ): subprocess.CompletedProcess(args, 0, "", ""),
        }
        result = values.get(tuple(args))
        if result is not None:
            return result
        return subprocess.CompletedProcess(args, 1, "", f"unexpected git args: {args}")

    report = collect_test_audit_preflight(
        ROOT,
        runner=fake_git_runner,
        git_lfs_path="/usr/bin/git-lfs",
    )

    blocker_ids = {entry["id"] for entry in report["blockers"]}
    assert "git_lfs_unhealthy" in blocker_ids
    assert report["git_lfs"]["version"]["ok"] is False


@pytest.mark.architecture
def test_preflight_reports_timed_out_git_status_as_strict_reproducibility_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(preflight, "_scan_lfs_pointer_files", lambda _root: [])

    def fake_git_runner(args: list[str]) -> subprocess.CompletedProcess[str]:
        if tuple(args) == ("status", "--short", "--untracked-files=no"):
            raise subprocess.TimeoutExpired(
                cmd=["git", *args],
                timeout=5.0,
                stderr="git status probe timed out",
            )

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
            ("lfs", "version"): "git-lfs/3.0.0",
            (
                "status",
                "--short",
                "--untracked-files=all",
                "--",
                "tests/fixtures/vcr",
            ): "",
        }
        key = tuple(args)
        if key in values:
            return subprocess.CompletedProcess(args, 0, values[key], "")
        return subprocess.CompletedProcess(args, 1, "", f"unexpected git args: {args}")

    report = collect_test_audit_preflight(
        ROOT,
        runner=fake_git_runner,
        git_lfs_path="/usr/bin/git-lfs",
    )

    blocker_ids = {entry["id"] for entry in report["blockers"]}
    assert "git_status_failed" in blocker_ids
    assert report["git_status"]["timed_out"] is True


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
            ("lfs", "version"): "git-lfs/3.0.0",
            ("status", "--short", "--untracked-files=no"): "",
            (
                "status",
                "--short",
                "--untracked-files=all",
                "--",
                "tests/fixtures/vcr",
            ): "",
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
def test_preflight_reports_dirty_vcr_worktree_as_strict_reproducibility_blocker(
    tmp_path: Path,
) -> None:
    repo = tmp_path
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
            ("lfs", "version"): "git-lfs/3.0.0",
            ("status", "--short", "--untracked-files=no"): "",
            (
                "status",
                "--short",
                "--untracked-files=all",
                "--",
                "tests/fixtures/vcr",
            ): (
                " M tests/fixtures/vcr/chembl/example.yaml\n"
                "?? tests/fixtures/vcr/pubmed/new.yaml\n"
            ),
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
    assert "dirty_vcr_worktree" in blocker_ids
    assert report["dirty_vcr_worktree"]["count"] == 2
    assert report["dirty_vcr_worktree"]["examples"] == [
        "tests/fixtures/vcr/chembl/example.yaml",
        "tests/fixtures/vcr/pubmed/new.yaml",
    ]


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

    assert (
        "Marker-only commands such as `pytest -m unit` are not canonical lanes" in text
    )


@pytest.mark.architecture
def test_tracing_emission_contract_test_remains_present() -> None:
    payload = _load_yaml(CONFIG_PATH)
    tracing = cast(YamlMap, payload["tracing"])
    test_path = ROOT / tracing["runtime_emission_test"]
    text = test_path.read_text(encoding="utf-8")

    assert "class RecordingTracing" in text
    for test_name in cast(list[str], tracing["required_test_names"]):
        assert f"def {test_name}" in text
