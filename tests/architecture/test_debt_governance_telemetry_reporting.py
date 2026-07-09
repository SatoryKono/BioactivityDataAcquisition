"""Architecture guardrails for unified debt-governance telemetry reporting."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest
import yaml

from scripts.engineering.qa.report_dead_code_inventory import build_dead_code_inventory
from scripts.engineering.qa.report_test_governance_audit import (
    collect_test_governance_report,
)

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_UUID_YAML = ROOT / "configs" / "quality" / "runtime_uuid_seams.yaml"

pytestmark = pytest.mark.timeout(240)


def _load_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, str(path.resolve()))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_compatibility_telemetry_module() -> ModuleType:
    return _load_module(
        ROOT / "scripts" / "engineering" / "ci" / "_compatibility_telemetry.py",
        "debt_governance_telemetry_reporting",
    )


@pytest.mark.architecture
def test_debt_governance_snapshot_matches_live_sources() -> None:
    """Unified debt-governance snapshot should stay aligned with live inventories."""
    telemetry = _load_compatibility_telemetry_module()
    snapshot = telemetry.collect_debt_governance_snapshot()

    runtime_uuid_inventory = yaml.safe_load(
        RUNTIME_UUID_YAML.read_text(encoding="utf-8")
    )
    assert isinstance(runtime_uuid_inventory, dict)
    seams = runtime_uuid_inventory.get("seams", [])
    assert isinstance(seams, list)

    dead_code_inventory = build_dead_code_inventory(ROOT)
    dead_code_summary = dead_code_inventory.get("summary", {})
    assert isinstance(dead_code_summary, dict)

    test_governance = collect_test_governance_report(ROOT)
    test_governance_summary = test_governance["summary"]

    assert snapshot.runtime_uuid.runtime_uuid_seam_count == len(
        [entry for entry in seams if isinstance(entry, dict)]
    )
    assert snapshot.runtime_uuid.replay_critical_uuid_seam_count == sum(
        1 for entry in seams if isinstance(entry, dict) and entry.get("replay_critical")
    )
    assert snapshot.retirement.triaged_entry_count == int(
        dead_code_summary["triaged_entry_count"]
    )
    assert snapshot.retirement.repo_wide_zero_import_candidate_count == int(
        dead_code_summary["repo_wide_zero_import_candidate_count"]
    )
    assert snapshot.retirement.repo_wide_classified_zero_import_candidate_count == int(
        dead_code_summary["repo_wide_classified_zero_import_candidate_count"]
    )
    assert snapshot.retirement.repo_wide_untriaged_zero_import_candidate_count == int(
        dead_code_summary["repo_wide_untriaged_zero_import_candidate_count"]
    )
    assert snapshot.retirement.repo_wide_owner_test_anchored_candidate_count == int(
        dead_code_summary["repo_wide_owner_test_anchored_candidate_count"]
    )
    assert snapshot.retirement.repo_wide_candidates_without_owner_tests_count == int(
        dead_code_summary["repo_wide_candidates_without_owner_tests_count"]
    )
    assert snapshot.retirement.repo_wide_non_static_reachability_candidate_count == int(
        dead_code_summary["repo_wide_non_static_reachability_candidate_count"]
    )
    assert snapshot.retirement.triaged_retained_owner_test_anchored_count == int(
        dead_code_summary["triaged_retained_owner_test_anchored_count"]
    )
    assert snapshot.retirement.triaged_retained_without_owner_tests_count == int(
        dead_code_summary["triaged_retained_without_owner_tests_count"]
    )
    assert snapshot.test_governance.compatibility_test_files == int(
        test_governance_summary["compatibility_test_files"]
    )
    assert snapshot.test_governance.refined_assertless_tests == int(
        test_governance_summary["refined_assertless_tests"]
    )
    assert snapshot.test_governance.markerless_test_functions == int(
        test_governance_summary["markerless_test_functions"]
    )
    assert snapshot.test_governance.duplicate_test_names == int(
        test_governance_summary["duplicate_test_names"]
    )
    assert snapshot.test_governance.duplicate_test_name_occurrences == int(
        test_governance_summary["duplicate_test_name_occurrences"]
    )
    assert snapshot.test_governance.uuid4_call_sites == int(
        test_governance_summary["uuid4_call_sites"]
    )
    assert snapshot.test_governance.date_today_call_sites == int(
        test_governance_summary["date_today_call_sites"]
    )


@pytest.mark.architecture
def test_debt_governance_summary_section_lists_required_metrics() -> None:
    """Rendered telemetry section should expose stable unified debt metric names."""
    telemetry = _load_compatibility_telemetry_module()
    snapshot = telemetry.collect_debt_governance_snapshot()
    section = telemetry.render_debt_governance_section(
        snapshot, heading="## Debt Governance Surface Snapshot"
    )

    assert section.startswith("## Debt Governance Surface Snapshot")
    for key in (
        "curated_inventory_rows",
        "runtime_uuid_seam_count",
        "replay_critical_uuid_seam_count",
        "triaged_entry_count",
        "repo_wide_zero_import_candidate_count",
        "repo_wide_classified_zero_import_candidate_count",
        "repo_wide_untriaged_zero_import_candidate_count",
        "repo_wide_owner_test_anchored_candidate_count",
        "repo_wide_candidates_without_owner_tests_count",
        "repo_wide_non_static_reachability_candidate_count",
        "triaged_retained_owner_test_anchored_count",
        "triaged_retained_without_owner_tests_count",
        "compatibility_test_files",
        "refined_assertless_tests",
        "markerless_test_functions",
        "duplicate_test_names",
        "duplicate_test_name_occurrences",
        "uuid4_call_sites",
        "date_today_call_sites",
    ):
        assert f"- {key}: `" in section
