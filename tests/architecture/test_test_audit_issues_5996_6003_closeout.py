"""Closeout guards for Test Audit issues #5996-#6003."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "test-audit-issues-5996-6003-closeout.json"
GOLD_WRITER_TEST = (
    ROOT / "tests" / "unit" / "infrastructure" / "storage" / "test_gold_writer.py"
)
COMPOSITE_GOLDEN_TEST = ROOT / "tests" / "contract" / "test_composite_merge_golden.py"
TEST_CONFTEST = ROOT / "tests" / "conftest.py"


def _load_closeout() -> dict[str, Any]:
    payload = json.loads(CLOSEOUT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _test_function_names(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(module)
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
        and node.name.startswith("test_")
    }


@pytest.mark.architecture
def test_5996_6003_closeout_evidence_covers_requested_issues() -> None:
    """The closeout artifact must explicitly cover every requested issue."""
    closeout = _load_closeout()

    assert closeout["schema_version"] == "test-audit-closeout-v1"
    assert closeout["issue_batch"]["issues"] == [
        5996,
        5997,
        5998,
        6000,
        6001,
        6002,
        6003,
    ]
    assert closeout["closeout"]["status"] == "complete"
    assert closeout["closeout"]["closeable_issues"] == [
        5996,
        5997,
        5998,
        6000,
        6001,
        6002,
        6003,
    ]
    assert closeout["closeout"]["deferred_issues"] == []


@pytest.mark.architecture
def test_5996_corrected_evidence_does_not_grow_debt_budgets() -> None:
    """Rebased evidence must remove stale findings without increasing debt budgets."""
    closeout = _load_closeout()
    corrected = closeout["corrected_audit_evidence"]
    gates = closeout["governance_gates"]

    assert corrected["debt_budget_growth_allowed"] is False
    assert gates["debt_budget_growth"] is False
    corrections = {
        item["finding"]: item["correction"]
        for item in corrected["removed_or_reframed_findings"]
    }
    assert "Add orjson to dependencies" in corrections
    assert "Enable xdist for unit tests" in corrections
    assert "Raise Windows xdist default cap" in corrections


@pytest.mark.architecture
def test_5997_dataframe_assertions_are_classified_before_modification() -> None:
    """DataFrame assertions must be classified, not blindly sorted."""
    closeout = _load_closeout()
    by_path = {
        item["path"]: item for item in closeout["dataframe_assertion_classification"]
    }

    assert closeout["governance_gates"]["blind_dataframe_sorting"] is False
    assert by_path["tests/unit/application/composite/test_merger.py"]["decision"] == (
        "retain_exact_order_assertions"
    )
    assert by_path["tests/integration/infrastructure/storage/test_silver_writer.py"][
        "classification"
    ] == ("already_deterministic")
    assert by_path["tests/contract/test_composite_merge_golden.py"]["decision"] == (
        "add_explicit_height_guards"
    )

    source = COMPOSITE_GOLDEN_TEST.read_text(encoding="utf-8")
    assert "assert seed_df.height == 1" in source
    assert "assert enricher_df.height == 1" in source


@pytest.mark.architecture
def test_5998_processed_records_http_interface_has_focused_coverage() -> None:
    """Processed Records HTTP payload coverage must be backed by a focused run."""
    closeout = _load_closeout()
    evidence = closeout["outcomes"]["5998"]["coverage_evidence"]

    assert evidence["baseline_inventory_coverage_percent"] == 35.29
    assert evidence["focused_module_coverage_percent"] >= 95.0
    assert "test_processed_records_table.py" in evidence["command"]
    assert "bioetl.interfaces.http.processed_records_table" in evidence["command"]


@pytest.mark.architecture
def test_6000_gold_writer_duplication_audit_covers_live_write_gold_tests() -> None:
    """Behavioral consolidation must be backed by a live test-name matrix."""
    closeout = _load_closeout()
    matrix = closeout["test_gold_writer_behavior_matrix"]
    live_tests = _test_function_names(GOLD_WRITER_TEST)
    matrix_tests = {
        test_name
        for family in matrix["behavior_families"]
        for test_name in family["tests"]
    }

    assert matrix["consolidation_requires_behavior_match"] is True
    assert matrix_tests <= live_tests
    assert {
        "test_write_gold_overwrite_mode",
        "test_write_gold_scd2_merge_existing_table",
        "test_write_gold_merged_with_strict_schema_passes",
    } <= matrix_tests


@pytest.mark.architecture
def test_6001_deprecated_api_removal_is_scheduled_after_sunset() -> None:
    """Deprecated behavior tests must stay governed by explicit sunset windows."""
    closeout = _load_closeout()
    schedule = {
        item["surface"]: item for item in closeout["deprecated_api_removal_schedule"]
    }

    assert schedule["--silver-filter-only"]["sunset_date"] == "2026-09-30"
    assert (
        schedule["--silver-filter-only"]["canonical_surface"] == "FILTERED_OUT_SILVER"
    )
    assert schedule["run_id compatibility aliases in HTTP/control-plane contracts"][
        "sunset_date"
    ] == ("2026-12-31")
    assert "caller audit" in schedule["--silver-filter-only"]["removal_rule"]


@pytest.mark.architecture
def test_6002_windows_xdist_stays_opt_in_without_default_cap_growth() -> None:
    """Windows xdist can be opted into without raising the conservative default."""
    closeout = _load_closeout()
    policy = closeout["windows_xdist_policy"]
    conftest_source = TEST_CONFTEST.read_text(encoding="utf-8")

    assert policy["default_cap"] == 1
    assert policy["opt_in_env"] == "BIOETL_PYTEST_WINDOWS_XDIST_WORKERS"
    assert policy["default_cap_increased"] is False
    assert closeout["governance_gates"]["windows_default_cap_increase"] is False
    assert "_DEFAULT_WINDOWS_XDIST_WORKER_CAP = 1" in conftest_source
    assert "BIOETL_PYTEST_WINDOWS_XDIST_WORKERS" in conftest_source


@pytest.mark.architecture
def test_6003_fixture_scope_optimization_requires_state_isolation_proof() -> None:
    """Fixture scope changes must be blocked until isolation evidence exists."""
    closeout = _load_closeout()
    policy = closeout["fixture_scope_policy"]

    assert policy["broad_scope_changes_made"] is False
    assert policy["requires_state_isolation_proof"] is True
    assert closeout["governance_gates"]["fixture_scope_change_without_proof"] is False
    assert (
        "test order randomization passes"
        in policy["required_evidence_before_scope_increase"]
    )
