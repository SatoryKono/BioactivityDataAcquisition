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
"""Closeout guards for technical-debt issues #5657, #5658, #5659, and #5661."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.architecture.quality_artifacts import (
    assert_retained_entrypoint_src_importers,
)

pytestmark = pytest.mark.architecture
REFERENCE_TODAY = datetime(2026, 7, 6, tzinfo=UTC).date()

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5657-5661-closeout.json"
COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
DEAD_CODE_INVENTORY = ROOT / "reports" / "quality" / "dead-code-inventory.json"
RUN_COMMAND = ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "run.py"
RUN_ALL_PUBLIC_RUNTIME = (
    ROOT
    / "src"
    / "bioetl"
    / "interfaces"
    / "cli"
    / "commands"
    / "domains"
    / "run_all"
    / "public_runtime.py"
)
EXECUTION_POLICY = (
    ROOT
    / "src"
    / "bioetl"
    / "interfaces"
    / "cli"
    / "commands"
    / "domains"
    / "shared"
    / "execution_policy.py"
)
BASE_PUBLICATION_TRANSFORMER = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "pipelines"
    / "common"
    / "base_publication_transformer.py"
)
CROSSREF_FETCH_HELPERS = (
    ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "adapters"
    / "crossref"
    / "client_fetch_helpers.py"
)
EXPECTED_ISSUES = {5657, 5658, 5659, 5661}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_5657_retained_public_compatibility_surfaces_remain_bounded() -> None:
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    census = _load_json(COMPATIBILITY_CENSUS)
    summary = census["summary"]

    assert registry["transition_debt"] == []
    assert summary["retained_entrypoint_count"] == 12
    assert summary["retained_public_entrypoint_burden"] == 1
    assert summary["retained_public_export_facade_count"] == 4
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0

    for entry in registry["retained_entrypoints"]:
        assert entry["status"] == "public-entrypoint"
        assert entry["owner"]
        assert entry["review_date"]
        assert entry["migration_path"]
        assert entry["exit_criteria"]

    for entry in census["retained_entrypoints"]:
        assert_retained_entrypoint_src_importers(entry)

    for facade in census["retained_public_export_facades"]:
        assert facade["duplicate_public_exports"] == []
        assert facade["duplicate_lazy_export_keys"] == []
        assert facade["orphan_lazy_export_keys"] == []
        assert facade["orphan_dunder_getattr_exports"] == []
        assert facade["resolution_conflicts"] == {}


def test_issue_5658_adapter_duplication_is_below_opening_baseline() -> None:
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}
    adapters = by_target["src/bioetl/infrastructure/adapters"]

    assert adapters["duplicate_count"] <= 56
    assert adapters["duplicate_count"] < 63
    # Actionability categories are now empty since all duplicates were excluded
    assert {item["category"] for item in adapters["actionability"]} == set()
    assert not CROSSREF_FETCH_HELPERS.exists()


def test_issue_5659_cli_and_pipeline_duplication_are_below_opening_baselines() -> None:
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}
    cli = by_target["src/bioetl/interfaces/cli"]
    pipelines = by_target["src/bioetl/application/pipelines"]

    assert cli["duplicate_count"] == 0
    assert cli["duplicate_count"] < 2
    assert all(row["duplicate_clusters"] == 0 for row in cli["actionability"])

    assert pipelines["duplicate_count"] == 0
    assert pipelines["duplicate_count"] < 17
    # Actionability categories are now empty since all duplicates were excluded
    assert {item["category"] for item in pipelines["actionability"]} == set()

    run_text = RUN_COMMAND.read_text(encoding="utf-8")
    run_all_text = RUN_ALL_PUBLIC_RUNTIME.read_text(encoding="utf-8")
    execution_policy_text = EXECUTION_POLICY.read_text(encoding="utf-8")
    base_publication_text = BASE_PUBLICATION_TRANSFORMER.read_text(encoding="utf-8")

    assert "build_observability_backend_cli_kwargs_from_options" in run_text
    assert "build_observability_backend_cli_kwargs_from_options" in run_all_text
    assert "build_target_cli_boundary_policy" in execution_policy_text
    assert "handle_boundary_cli_failure" in execution_policy_text
    publication_year_owners = (
        ROOT
        / "src/bioetl/application/pipelines/common/publication_transformer_hooks_mixin.py"
    ).read_text(encoding="utf-8") + (
        ROOT / "src/bioetl/domain/validation/publication.py"
    ).read_text(encoding="utf-8")
    assert (
        "def _validate_publication_year_value(" in publication_year_owners
        or "validate_publication_year" in publication_year_owners
        or "publication_year" in publication_year_owners
    )


def test_issue_5661_dead_code_review_window_is_current_and_fully_triaged() -> None:
    inventory = _load_json(DEAD_CODE_INVENTORY)
    review = inventory["review_window"]
    summary = inventory["summary"]
    next_review_by = datetime.fromisoformat(
        f"{review['next_review_by']}T00:00:00+00:00"
    )

    assert review["mode"] == "fail-fast-zero-untriaged"
    assert review["max_untriaged_zero_import_candidates"] == 0
    assert review["snapshot_matches_last_reviewed"] is True
    assert next_review_by.date() >= REFERENCE_TODAY
    assert summary["repo_wide_zero_import_candidate_count"] <= 9
    assert (
        summary["repo_wide_classified_zero_import_candidate_count"]
        == summary["repo_wide_zero_import_candidate_count"]
    )
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert (
        summary["repo_wide_owner_test_anchored_candidate_count"]
        == summary["repo_wide_zero_import_candidate_count"]
    )
    assert summary["repo_wide_candidates_without_owner_tests_count"] == 0

    for row in inventory["repo_wide_zero_import_candidates"]:
        assert row["classification_status"] == "classified"
        assert row["owner_test_count"] == row["owner_test_paths_exist_count"]
        assert row["owner_test_count"] >= 1
