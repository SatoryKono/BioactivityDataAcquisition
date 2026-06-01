"""Architecture checks for the 2026-05-15 test-governance issue pack."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from scripts.engineering.qa import check_test_audit_preflight as preflight
from scripts.engineering.qa.check_test_audit_preflight import (
    STRICT_BLOCKER_IDS,
    collect_test_audit_preflight,
)
from scripts.engineering.qa.report_test_governance_audit import (
    collect_test_governance_report,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "quality" / "test_governance_audit.yaml"
DUPLICATE_NAME_INVENTORY_PATH = (
    ROOT / "reports" / "quality" / "test-duplicate-name-inventory.json"
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
    "tests/unit/grafana/test_silver_reject_explorer_copy.py": (
        "tests/integration/grafana/test_silver_reject_explorer_copy.py"
    ),
}
REPO_BACKED_UNIT_MARKERS = (
    re.compile(
        r'Path\("(?:(?:configs|docs|grafana|scripts|src|tests/fixtures)/[^"]+)"\)\.(?:read_text|read_bytes|resolve)\('
    ),
    re.compile(r"Path\(__file__\)\.resolve\(\)\.parents\[(3|4)\]"),
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

    assert command in workflow
    assert workflow.index(command) < workflow.index(
        "Observability metric inventory drift gate"
    )


@pytest.mark.architecture
def test_compatibility_test_file_max_follows_stream_g_downward_ratchet() -> None:
    """#4826: compatibility_test_file_max may only ratchet down to the live inventory."""
    payload = _load_yaml(CONFIG_PATH)
    report = collect_test_governance_report(ROOT)
    budgets = cast(YamlMap, payload["budgets"])
    ratchet = cast(YamlMap, payload["budget_ratchet"])

    live_count = int(report["compatibility_test_files"])
    budget_max = int(budgets["compatibility_test_file_max"])
    target_count = 53

    owner_notes = cast(list[YamlMap], ratchet.get("stream_g_owner_notes", []))
    issue_notes = [note for note in owner_notes if note.get("issue") == "#4826"]
    assert issue_notes, "Stream G owner note for #4826 must be recorded"

    assert live_count <= budget_max
    if live_count <= target_count:
        assert budget_max == target_count, (
            "compatibility_test_file_max must ratchet down to 53 when live inventory "
            f"is at or below target; live={live_count}, budget={budget_max}"
        )
    else:
        assert budget_max == live_count, (
            "compatibility_test_file_max must pin to the live inventory while count "
            f"exceeds target 54; live={live_count}, budget={budget_max}"
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
    payload = _load_yaml(CONFIG_PATH)
    cache_policy = cast(YamlMap, payload["slow_governance_scanner_cache"])

    first = collect_test_governance_report(ROOT)
    second = collect_test_governance_report(ROOT)

    assert cache_policy["decision"] == "retained_cached_scanner"
    assert cache_policy["issue_ref"] == "#4663"
    assert first is second
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
def test_duplicate_name_inventory_artifact_matches_static_report() -> None:
    payload = json.loads(DUPLICATE_NAME_INVENTORY_PATH.read_text(encoding="utf-8"))
    report = collect_test_governance_report(ROOT)

    assert payload["summary"] == report["duplicate_test_name_inventory_summary"]
    assert payload["inventory"] == report["duplicate_test_name_inventory"]


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
        assert actual_lines == int(entry["lines"])
        assert actual_lines <= max_lines
        assert cast(str, entry["owner"]).strip()
        assert cast(str, entry["target_split"]).strip()

    for split in cast(list[YamlMap], inventory.get("completed_splits", [])):
        source = ROOT / cast(str, split["source"])
        extracted = ROOT / cast(str, split["extracted_surface"])
        assert source.exists()
        assert extracted.exists()
        assert len(source.read_text(encoding="utf-8").splitlines()) == int(
            split["source_lines_after_split"]
        )
        assert len(extracted.read_text(encoding="utf-8").splitlines()) == int(
            split["extracted_surface_lines"]
        )


@pytest.mark.architecture
def test_compatibility_inventory_covers_every_detected_compatibility_test_file() -> (
    None
):
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
        if repo_relative_match or repo_root_match:
            detected_paths.add(path.relative_to(ROOT).as_posix())

    assert policy["decision"] == "retained_repo_backed_contract_exception"
    assert cast(str, policy["rationale"]).strip()
    assert cast(str, policy["review_date"]) >= "2026-05-20"
    assert configured_paths == detected_paths - domain_contract_paths
    for entry in entries:
        assert (ROOT / cast(str, entry["path"])).exists()
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
        == "retained_logical_unit_ownership_with_curated_repo_backed_exceptions"
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
def test_preflight_reports_unhealthy_git_lfs_as_strict_reproducibility_blocker() -> (
    None
):
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
def test_preflight_reports_timed_out_git_status_as_strict_reproducibility_blocker() -> (
    None
):
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
