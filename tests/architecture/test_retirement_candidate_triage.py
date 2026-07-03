"""Architecture guardrails for zero-anchor retirement triage decisions."""

from __future__ import annotations

import pytest

import ast
from collections import Counter
from datetime import date, timedelta
import json
from functools import cache
from pathlib import Path

import yaml

from scripts.engineering.qa.report_dead_code_inventory import (
    _review_window_is_stale,
    _render_markdown,
    build_dead_code_inventory,
)

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRIAGE_PATH = PROJECT_ROOT / "configs/quality/retirement_candidate_triage.yaml"
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
SRC_ROOT = PROJECT_ROOT / "src" / "bioetl"
DEAD_CODE_JSON_PATH = PROJECT_ROOT / "reports" / "quality" / "dead-code-inventory.json"
DEAD_CODE_MD_PATH = PROJECT_ROOT / "reports" / "quality" / "dead-code-inventory.md"


def _load_triage() -> dict[str, object]:
    payload = yaml.safe_load(TRIAGE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_scorecard() -> dict[str, object]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _iter_triage_entries(triage: dict[str, object]) -> list[dict[str, object]]:
    return [
        entry
        for family in triage.get("families", [])
        if isinstance(family, dict)
        for entry in family.get("entries", [])
        if isinstance(entry, dict)
    ]


def _iter_repo_wide_zero_import_entries(
    triage: dict[str, object],
) -> list[dict[str, object]]:
    section = triage.get("repo_wide_zero_import_classification", {})
    assert isinstance(section, dict)
    entries = section.get("entries", [])
    assert isinstance(entries, list)
    return [entry for entry in entries if isinstance(entry, dict)]


@cache
def _iter_src_python_files() -> tuple[Path, ...]:
    return tuple(sorted(SRC_ROOT.rglob("*.py")))


def _file_imports_module(path: Path, module_name: str) -> bool:
    """Return True when the file imports the requested module."""
    return module_name in _absolute_import_targets_for_file(path)


def _absolute_import_targets_for_file(path: Path) -> frozenset[str]:
    """Return absolute module targets imported by one source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom) or node.level != 0:
            continue
        if node.module is None:
            continue
        targets.add(node.module)
        targets.update(
            f"{node.module}.{alias.name}" for alias in node.names if alias.name != "*"
        )
    return frozenset(targets)


@cache
def _src_importer_counts() -> Counter[str]:
    """Count source importers once per module target for the whole test file."""
    counts: Counter[str] = Counter()
    for path in _iter_src_python_files():
        counts.update(_absolute_import_targets_for_file(path))
    return counts


def _count_src_importers(module_name: str) -> int:
    return _src_importer_counts()[module_name]


def test_retirement_triage_entries_are_explicit_and_actionable() -> None:
    """Each tracked retirement tranche should declare a concrete decision."""
    triage = _load_triage()
    assert triage.get("schema_version") == 1
    policy = triage.get("policy", {})
    assert isinstance(policy, dict)
    assert policy.get("review_cycle_days") == 90
    zero_import_review = triage.get("repo_wide_zero_import_review", {})
    assert isinstance(zero_import_review, dict)
    assert zero_import_review.get("linked_issue") == "#4541"
    assert zero_import_review.get("mode") == "fail-fast-zero-untriaged"
    assert isinstance(zero_import_review.get("inventory_command"), str)
    assert "report_dead_code_inventory" in zero_import_review["inventory_command"]
    assert isinstance(zero_import_review.get("check_command"), str)
    assert "--check" in zero_import_review["check_command"]
    assert isinstance(
        zero_import_review.get("max_untriaged_zero_import_candidates"), int
    )
    assert isinstance(zero_import_review.get("last_reviewed"), str)
    assert isinstance(zero_import_review.get("next_review_by"), str)

    families = triage.get("families", [])
    assert isinstance(families, list) and families
    entries = list(_iter_triage_entries(triage))
    assert entries, "Expected at least one retirement-triage entry"
    repo_wide = triage.get("repo_wide_zero_import_classification", {})
    assert isinstance(repo_wide, dict)
    assert repo_wide.get("linked_issue") == "#4541"
    assert repo_wide.get("review_date") == "2026-06-16"
    assert set(repo_wide.get("allowed_dispositions", [])) == {
        "retain_module_entrypoint",
        "retain_dynamic_entrypoint",
        "retain_public_facade",
        "retain_compat_shim",
        "retain_canonical_owner_module",
    }
    assert _iter_repo_wide_zero_import_entries(triage)

    for entry in entries:
        disposition = entry.get("disposition")
        assert disposition in {"removed", "retain_active"}
        assert isinstance(entry.get("rationale"), str) and entry["rationale"].strip()
        assert isinstance(entry.get("reviewed_on"), str) and entry["reviewed_on"]
        assert isinstance(entry.get("linked_issue"), str) and entry["linked_issue"]

        target = entry.get("target", {})
        assert isinstance(target, dict)
        module_path = target.get("module_path")
        assert isinstance(module_path, str) and module_path

        if disposition == "retain_active":
            assert isinstance(entry.get("review_by"), str) and entry["review_by"]
            verification = entry.get("verification", {})
            assert isinstance(verification, dict)
            min_src_importers = verification.get("min_src_importers")
            assert isinstance(min_src_importers, int) and min_src_importers >= 1


def test_removed_retirement_tranches_stay_absent() -> None:
    """Removed retirement tranches should not reappear in the source tree."""
    triage = _load_triage()
    entries = [
        entry
        for entry in _iter_triage_entries(triage)
        if entry.get("disposition") == "removed"
    ]
    assert entries, "Expected at least one removed retirement tranche"

    for entry in entries:
        target = entry["target"]
        assert isinstance(target, dict)
        module_path = target["module_path"]
        assert isinstance(module_path, str)
        assert not (PROJECT_ROOT / module_path).exists(), (
            f"Removed retirement tranche unexpectedly exists again: {module_path}"
        )


def test_retained_zero_anchor_tranches_have_live_src_importers() -> None:
    """Retained candidates must stay justified by first-party source imports."""
    triage = _load_triage()
    retained = [
        entry
        for entry in _iter_triage_entries(triage)
        if entry.get("disposition") == "retain_active"
    ]
    assert retained, "Expected at least one retained retirement tranche"

    for entry in retained:
        target = entry["target"]
        assert isinstance(target, dict)
        module_path = target["module_path"]
        module_name = target["module_name"]
        assert isinstance(module_path, str)
        assert isinstance(module_name, str)
        assert (PROJECT_ROOT / module_path).exists(), (
            f"Retained active tranche is missing its module: {module_path}"
        )

        verification = entry["verification"]
        assert isinstance(verification, dict)
        min_src_importers = verification["min_src_importers"]
        assert isinstance(min_src_importers, int)
        actual_importers = _count_src_importers(module_name)
        assert actual_importers >= min_src_importers, (
            f"{module_name} only has {actual_importers} src importers, below the "
            f"triaged minimum {min_src_importers}. Remove it or refresh the triage ledger intentionally."
        )


def test_neo4j_memory_calibration_candidates_match_triage_decisions() -> None:
    """Calibration candidates from the memory refresh must map to explicit triage decisions."""
    triage = _load_triage()
    triage_entries = {
        str(target["module_path"]): entry
        for entry in _iter_triage_entries(triage)
        if isinstance((target := entry.get("target", {})), dict)
        and isinstance(target.get("module_path"), str)
    }

    scorecard = _load_scorecard()
    calibration = scorecard.get("neo4j_memory_calibration", {})
    assert isinstance(calibration, dict)
    assert calibration.get("snapshot_date") == "2026-04-13"
    assert (
        isinstance(calibration.get("update_policy"), str)
        and calibration["update_policy"]
    )

    families = calibration.get("families", [])
    assert isinstance(families, list) and families

    for family in families:
        assert isinstance(family, dict)
        assert isinstance(family.get("linked_issue"), str) and family["linked_issue"]
        candidates = family.get("candidates", [])
        assert isinstance(candidates, list) and candidates
        for candidate in candidates:
            assert isinstance(candidate, dict)
            module_path = candidate.get("module_path")
            expected_disposition = candidate.get("expected_disposition")
            assert isinstance(module_path, str) and module_path
            assert expected_disposition in {"removed", "retain_active"}
            triage_entry = triage_entries.get(module_path)
            assert triage_entry is not None, (
                f"{module_path} is tracked in neo4j_memory_calibration but missing from "
                "retirement_candidate_triage.yaml."
            )
            assert triage_entry.get("disposition") == expected_disposition, (
                f"{module_path} is calibrated as {expected_disposition} but triage marks it "
                f"as {triage_entry.get('disposition')}."
            )


def test_repo_wide_zero_import_candidate_count_does_not_grow() -> None:
    """Repo-wide zero-import candidates must stay fully classified under budget."""
    triage = _load_triage()
    zero_import_review = triage["repo_wide_zero_import_review"]
    assert isinstance(zero_import_review, dict)
    budget = zero_import_review["max_untriaged_zero_import_candidates"]
    assert isinstance(budget, int)

    inventory = build_dead_code_inventory(PROJECT_ROOT)
    summary = inventory["summary"]
    assert isinstance(summary, dict)
    actual = summary["repo_wide_untriaged_zero_import_candidate_count"]
    assert isinstance(actual, int)

    assert actual <= budget, (
        f"Repo-wide untriaged zero-import candidate count grew to {actual}, above the "
        f"reviewed budget {budget}. Remove candidates or refresh "
        "retirement_candidate_triage.yaml intentionally."
    )


def test_repo_wide_zero_import_classification_exactly_covers_candidates() -> None:
    """Every repo-wide zero-import candidate must have one explicit classification."""
    triage = _load_triage()
    classified = {
        str(entry["module_path"]): entry
        for entry in _iter_repo_wide_zero_import_entries(triage)
    }

    inventory = build_dead_code_inventory(PROJECT_ROOT)
    zero_candidates = inventory["repo_wide_zero_import_candidates"]
    assert isinstance(zero_candidates, list)
    actual_paths = {str(row["path"]) for row in zero_candidates}

    assert set(classified) == actual_paths
    for _path, entry in classified.items():
        assert isinstance(entry.get("module_name"), str) and entry["module_name"]
        assert isinstance(entry.get("disposition"), str) and entry["disposition"]
        assert isinstance(entry.get("reviewed_on"), str) and entry["reviewed_on"]
        assert isinstance(entry.get("review_by"), str) and entry["review_by"]
        assert isinstance(entry.get("linked_issue"), str) and entry["linked_issue"]
        assert isinstance(entry.get("rationale"), str) and entry["rationale"].strip()


def test_retained_zero_import_rows_have_owner_test_evidence() -> None:
    """Retained zero-import residue must materialize explicit owner-test evidence."""
    inventory = build_dead_code_inventory(PROJECT_ROOT)
    summary = inventory["summary"]
    assert isinstance(summary, dict)

    zero_candidates = inventory["repo_wide_zero_import_candidates"]
    assert isinstance(zero_candidates, list)
    for row in zero_candidates:
        assert isinstance(row.get("evidence_lane"), str) and row["evidence_lane"]
        assert int(row["owner_test_count"]) > 0, (
            f"Repo-wide zero-import candidate lacks owner tests: {row['path']}"
        )
        assert int(row["owner_test_count"]) == int(
            row["owner_test_paths_exist_count"]
        ), f"Owner-test paths drifted for repo-wide zero-import candidate: {row['path']}"

    triaged_rows = inventory["triaged_entries"]
    assert isinstance(triaged_rows, list)
    for row in triaged_rows:
        if row.get("disposition") != "retain_active":
            continue
        assert isinstance(row.get("evidence_lane"), str) and row["evidence_lane"]
        assert int(row["owner_test_count"]) > 0, (
            f"Retained triage row lacks owner tests: {row['module_path']}"
        )
        assert int(row["owner_test_count"]) == int(
            row["owner_test_paths_exist_count"]
        ), f"Owner-test paths drifted for retained triage row: {row['module_path']}"

    assert summary["repo_wide_owner_test_anchored_candidate_count"] == len(
        zero_candidates
    )
    assert summary["repo_wide_candidates_without_owner_tests_count"] == 0
    assert summary["triaged_retained_without_owner_tests_count"] == 0
    retained_triage_count = sum(
        1 for row in triaged_rows if row.get("disposition") == "retain_active"
    )
    assert summary["triaged_retained_owner_test_anchored_count"] == retained_triage_count


def test_dead_code_inventory_artifacts_are_committed_and_current() -> None:
    """Dead-code review evidence must stay materialized for zero-import triage."""
    assert DEAD_CODE_JSON_PATH.exists()
    assert DEAD_CODE_MD_PATH.exists()

    committed = json.loads(DEAD_CODE_JSON_PATH.read_text(encoding="utf-8"))
    expected = build_dead_code_inventory(
        PROJECT_ROOT,
        snapshot_date=str(committed["snapshot_date"]),
    )

    assert committed == expected
    summary = committed["summary"]
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert DEAD_CODE_MD_PATH.read_text(encoding="utf-8") == _render_markdown(expected)


def test_dead_code_inventory_review_window_stays_fresh() -> None:
    """The repo-wide dead-code inventory must stay within the governed review window."""
    triage = _load_triage()
    policy = triage["policy"]
    assert isinstance(policy, dict)
    zero_import_review = triage["repo_wide_zero_import_review"]
    assert isinstance(zero_import_review, dict)

    review_cycle_days = policy["review_cycle_days"]
    assert isinstance(review_cycle_days, int)
    last_reviewed = date.fromisoformat(str(zero_import_review["last_reviewed"]))
    next_review_by = date.fromisoformat(str(zero_import_review["next_review_by"]))
    assert next_review_by == last_reviewed + timedelta(days=review_cycle_days), (
        "Dead-code zero-import review window must track policy.review_cycle_days "
        "from the last reviewed date."
    )
    committed = json.loads(DEAD_CODE_JSON_PATH.read_text(encoding="utf-8"))
    review_window = committed["review_window"]
    assert isinstance(review_window, dict)
    assert not _review_window_is_stale(review_window), (
        "Dead-code zero-import review window is stale. Refresh "
        "reports/quality/dead-code-inventory.{json,md} and advance "
        "repo_wide_zero_import_review.last_reviewed/next_review_by."
    )
    assert committed["snapshot_date"] == zero_import_review["last_reviewed"]
    assert review_window["linked_issue"] == zero_import_review["linked_issue"]
    assert review_window["last_reviewed"] == zero_import_review["last_reviewed"]
    assert review_window["next_review_by"] == zero_import_review["next_review_by"]
    assert review_window["review_cycle_days"] == review_cycle_days
    assert review_window["snapshot_matches_last_reviewed"] is True
