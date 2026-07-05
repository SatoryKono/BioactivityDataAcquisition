"""Closeout guards for technical-debt issues #5752 through #5755."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_MANIFEST = ROOT / "configs" / "quality" / "scripts_inventory_manifest.json"
SCRIPTS_REGISTRY = ROOT / "configs" / "quality" / "scripts_lifecycle_registry.json"
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
TEST_GOVERNANCE = ROOT / "reports" / "quality" / "test-governance-current.json"
SCORECARD = ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
DEBT_REPORT = ROOT / "reports" / "quality" / "total-tech-debt-audit-main-2026-07-01.md"
CURRENT_STATE = ROOT / "docs" / "02-architecture" / "current-state-inventory.md"
REPRO_SUITE = (
    ROOT / "tests" / "integration" / "ci" / "test_reproducibility_contract_suite.py"
)
FORENSIC_UNIT_TEST = (
    ROOT
    / "tests"
    / "unit"
    / "application"
    / "services"
    / "test_forensic_diff_service.py"
)

REMOVED_WRAPPERS = (
    "scripts/ai/codex/cursor-launch.ps1",
    "scripts/ai/codex/fix-nodejs.sh",
    "scripts/ai/gemini/clean-gemini-config.ps1",
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_5755_removed_supporting_wrappers_are_absent_and_untracked() -> None:
    manifest = _load_json(SCRIPTS_MANIFEST)
    registry = _load_json(SCRIPTS_REGISTRY)
    script_rows = manifest["scripts"]

    assert isinstance(script_rows, list)
    assert isinstance(registry["entries"], dict)

    for relative_path in REMOVED_WRAPPERS:
        assert not (ROOT / relative_path).exists()
        assert all(
            row.get("path") != relative_path
            for row in script_rows
            if isinstance(row, dict)
        )
        assert relative_path not in registry["entries"]

    summary = manifest["summary"]
    assert isinstance(summary, dict)
    status_counts = summary["status_counts"]
    assert isinstance(status_counts, dict)
    recomputed_status_counts = Counter(
        row.get("status") for row in script_rows if isinstance(row, dict)
    )
    assert summary["total_scripts"] == len(script_rows)
    assert status_counts == dict(sorted(recomputed_status_counts.items()))


def test_issue_5754_forensic_public_imports_use_canonical_seam() -> None:
    repro_suite = REPRO_SUITE.read_text(encoding="utf-8")
    forensic_unit = FORENSIC_UNIT_TEST.read_text(encoding="utf-8")

    assert (
        "from bioetl.application.services.control_plane.forensic import "
        "ForensicRunDiffService"
    ) in repro_suite
    assert (
        "from bioetl.application.services.control_plane.forensic import "
        "ForensicRunDiffService"
    ) in forensic_unit
    assert (
        "from bioetl.application.services.control_plane.forensic_diff_service import (\n"
        "    ForensicRunDiffService,"
    ) not in forensic_unit


def test_issue_5752_narrative_reports_match_live_governance_artifacts() -> None:
    compatibility = _load_json(COMPATIBILITY_CENSUS)
    test_governance = _load_json(TEST_GOVERNANCE)
    scorecard = _load_json(SCORECARD)
    gates = _load_json(DEBT_GATES)
    debt_report = DEBT_REPORT.read_text(encoding="utf-8")
    current_state = CURRENT_STATE.read_text(encoding="utf-8")

    assert compatibility["summary"]["retained_entrypoint_count"] == 12
    assert test_governance["report"]["compatibility_test_files"] == 0
    assert test_governance["report"]["duplicate_test_names"] == 1
    assert test_governance["report"]["markerless_test_functions"] == 0
    assert test_governance["report"]["total_test_functions"] == 21817
    assert test_governance["report"]["total_test_files"] == 1936
    assert scorecard["integral_score"] == 8.58
    assert gates["summary"]["release_gate_status"] == "passing"
    assert gates["summary"]["pass_count"] == gates["summary"]["gate_count"]
    assert gates["summary"]["fail_count"] == 0

    assert "Integral score is `8.58`" in debt_report
    assert "Retained entrypoints `12`" in debt_report
    assert "0 compatibility test files" in debt_report
    assert "91 supporting scripts" in debt_report
    assert "21,784 test functions, 1,930 test files" in debt_report

    assert (
        "| Architecture quality score | `8.58` (`good_targeted_improvements`) |"
        in current_state
    )
    assert "compatibility_test_files=0" in current_state
