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
"""Unit tests for committed governance artifact reuse in CI quality-gate."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from scripts.engineering.ci._compatibility_telemetry import (
    collect_retirement_governance_snapshot,
    collect_test_governance_snapshot,
)
from scripts.engineering.ci.quality_integral_gate import _resolve_architecture_stats

pytestmark = pytest.mark.unit

_RETIREMENT_SUMMARY = {
    "triaged_entry_count": 18,
    "repo_wide_zero_import_candidate_count": 3,
    "repo_wide_classified_zero_import_candidate_count": 3,
    "repo_wide_untriaged_zero_import_candidate_count": 0,
    "repo_wide_owner_test_anchored_candidate_count": 3,
    "repo_wide_candidates_without_owner_tests_count": 0,
    "repo_wide_non_static_reachability_candidate_count": 2,
    "triaged_retained_owner_test_anchored_count": 14,
    "triaged_retained_without_owner_tests_count": 0,
}

_TEST_GOVERNANCE_REPORT = {
    "compatibility_test_files": 0,
    "refined_assertless_tests": 2,
    "markerless_test_functions": 4,
    "duplicate_test_names": 1,
    "duplicate_test_name_occurrences": 2,
    "uuid4_call_sites": 5,
    "date_today_call_sites": 6,
}


def _write_committed_artifacts(repo_root: Path) -> None:
    quality_dir = repo_root / "reports" / "quality"
    quality_dir.mkdir(parents=True)
    (quality_dir / "dead-code-inventory.json").write_text(
        json.dumps({"summary": _RETIREMENT_SUMMARY}, indent=2) + "\n",
        encoding="utf-8",
    )
    (quality_dir / "test-governance-current.json").write_text(
        json.dumps({"report": _TEST_GOVERNANCE_REPORT}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_committed_retirement_snapshot_skips_live_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_committed_artifacts(tmp_path)

    def _fail(_repo_root: Path) -> None:
        raise AssertionError("live dead-code inventory must not run")

    monkeypatch.setattr(
        "scripts.engineering.ci._compatibility_telemetry.build_dead_code_inventory",
        _fail,
    )
    snapshot = collect_retirement_governance_snapshot(
        repo_root=tmp_path, artifact_source="committed"
    )
    assert snapshot.triaged_entry_count == 18
    assert snapshot.repo_wide_untriaged_zero_import_candidate_count == 0


def test_committed_test_governance_snapshot_skips_live_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_committed_artifacts(tmp_path)

    def _fail(_repo_root: Path) -> None:
        raise AssertionError("live test-governance scan must not run")

    monkeypatch.setattr(
        "scripts.engineering.ci._compatibility_telemetry.collect_test_governance_report",
        _fail,
    )
    snapshot = collect_test_governance_snapshot(
        repo_root=tmp_path, artifact_source="committed"
    )
    assert snapshot.refined_assertless_tests == 2
    assert snapshot.uuid4_call_sites == 5


def test_committed_retirement_snapshot_fails_closed_when_missing(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="dead-code-inventory.json"):
        collect_retirement_governance_snapshot(
            repo_root=tmp_path, artifact_source="committed"
        )


def test_committed_test_governance_snapshot_fails_closed_when_incomplete(
    tmp_path: Path,
) -> None:
    quality_dir = tmp_path / "reports" / "quality"
    quality_dir.mkdir(parents=True)
    (quality_dir / "test-governance-current.json").write_text(
        json.dumps({"report": {"compatibility_test_files": 0}}, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="refined_assertless_tests"):
        collect_test_governance_snapshot(
            repo_root=tmp_path, artifact_source="committed"
        )


def test_unknown_artifact_source_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="artifact_source"):
        collect_retirement_governance_snapshot(
            repo_root=tmp_path, artifact_source="cached"
        )


def test_lint_architecture_owner_still_skips_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail(_path: str) -> None:
        raise AssertionError("architecture pytest must not run for workflow owner")

    monkeypatch.setattr(
        "scripts.engineering.ci.quality_integral_gate._run_architecture_tests",
        _fail,
    )
    stats = _resolve_architecture_stats(
        Namespace(
            architecture_owner="lint-architecture-workflow",
            architecture_tests="tests/architecture",
        )
    )
    assert stats.owner == "lint-architecture-workflow"
    assert stats.returncode == 0
