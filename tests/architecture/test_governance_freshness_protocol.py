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
"""Architecture tests for governance freshness protocol markers."""

from __future__ import annotations

import re
import subprocess

import pytest

from pathlib import Path

import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_doc_publication_policy_documents_freshness_protocol() -> None:
    text = _read("docs/00-project/governance/06-doc-publication-policy.md")
    lower_text = text.lower()

    assert "## Freshness Protocol" in text
    assert "generated artifacts" in lower_text
    assert "summaries" in lower_text
    assert "dated reports" in lower_text
    assert "python -m scripts.docs check-drift --freshness" in text


def test_plans_index_documents_refresh_triggers() -> None:
    text = _read("docs/plans/README.md")

    assert "## Freshness Triggers" in text
    assert "Freshness note" in text
    assert "reports/plans/" in text


def test_evidence_index_declares_rebaseline_model() -> None:
    text = _read("docs/reports/evidence/INDEX.md").lower()

    assert "freshness model" in text
    assert "rebaseline" in text
    assert "historical" in text


def test_high_signal_reports_carry_freshness_notes() -> None:
    candidate_paths = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "docs" / "plans").glob("*2026-*.md"))
    ]
    assert candidate_paths, "Expected at least one high-signal dated report artifact"

    paths_with_freshness_note = []
    for relative_path in candidate_paths:
        text = _read(relative_path)
        if "Freshness note" in text:
            paths_with_freshness_note.append(relative_path)

    assert paths_with_freshness_note, (
        "Expected at least one high-signal dated report artifact with a Freshness note"
    )


def test_technical_debt_surfaces_mark_rebaseline_status() -> None:
    for relative_path in (
        "docs/reports/evidence/technical-debt/SUMMARY.md",
        "docs/reports/evidence/technical-debt/complexity-hotspots/SUMMARY.md",
        "docs/reports/evidence/technical-debt/03-synthesis/CROSS-SYNTHESIS.md",
    ):
        text = _read(relative_path).lower()
        assert "rebaseline" in text or "historical trigger evidence" in text, (
            f"{relative_path} is missing rebaseline guidance"
        )


def test_project_test_health_summary_is_evidence_only_with_freshness_note() -> None:
    text = _read("docs/reports/evidence/project-test-health/SUMMARY.md")
    lower_text = text.lower()

    assert "Freshness note" in text
    assert "non-canonical" in lower_text
    assert "repo-only evidence layer" in lower_text
    for canonical_source in (
        "configs/quality/test_matrix.yaml",
        "configs/quality/test_health_reporting.yaml",
        "configs/quality/fixture_governance_ledger.yaml",
    ):
        assert canonical_source in text
    assert "backlog signal only" in lower_text
    assert "fresh evidence-pack rebaseline" in lower_text


def test_project_test_health_summary_declares_machine_readable_freshness_metadata() -> (
    None
):
    text = _read("docs/reports/evidence/project-test-health/SUMMARY.md")
    assert text.startswith("---\n")
    metadata_text = text.split("\n---\n", maxsplit=2)[0].removeprefix("---\n")
    metadata = yaml.safe_load(metadata_text)

    assert metadata["status"] == "active-non-canonical"
    assert metadata["last_verified"].startswith("2026-")
    assert metadata["freshness_window_days"] > 0
    assert metadata["owner"] == "quality"
    assert set(metadata["canonical_sources"]) >= {
        "configs/quality/test_matrix.yaml",
        "configs/quality/test_health_reporting.yaml",
        "configs/quality/fixture_governance_ledger.yaml",
    }


def test_project_test_health_summary_has_machine_readable_metadata() -> None:
    metadata_path = (
        ROOT / "docs" / "reports" / "evidence" / "project-test-health" / "metadata.yaml"
    )
    shard_registry_path = (
        ROOT
        / "docs"
        / "reports"
        / "evidence"
        / "project-test-health"
        / "shard_registry.yaml"
    )

    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    shard_registry = yaml.safe_load(shard_registry_path.read_text(encoding="utf-8"))
    assert metadata["policy_scope"] == "non_canonical_evidence_summary"
    assert metadata["owner"]
    assert metadata["freshness_window_days"] >= 1
    assert metadata["last_verified"].startswith("2026-")
    assert metadata["allowed_interpretation"] == "backlog_signal_only"
    assert metadata["canonical_sources"]
    assert metadata["verification_scope"] == "tracked_test_module_inventory"
    source_ref = metadata["source_ref"]
    assert isinstance(source_ref, str)
    assert re.fullmatch(r"[0-9a-f]{40}", source_ref)
    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_ref, "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )
    inventory = metadata["test_module_inventory"]
    tracked_test_modules = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "tests/**/test_*.py"], cwd=ROOT
    ).split(b"\0")
    tracked_test_module_count = len([path for path in tracked_test_modules if path])
    assert inventory == {
        "command": "git ls-files 'tests/**/test_*.py' | wc -l",
        "count": tracked_test_module_count,
        "counted_on": metadata["last_verified"],
        "full_evidence_snapshot_date": "2026-03-23",
    }
    assert shard_registry["policy_scope"] == "project_test_health_evidence_shards"
    assert shard_registry["owner"]
    assert shard_registry["last_inventory_rebaseline"] == inventory["counted_on"]
    assert shard_registry["inventory_source_ref"] == metadata["source_ref"]
    assert shard_registry["inventory_scope"] == metadata["verification_scope"]
    assert shard_registry["shards"]

    resolved_shards = {
        shard["id"]
        for shard in shard_registry["shards"]
        if shard.get("status") == "passed"
    }
    assert {
        "flaky-rate",
        "uncovered-module-risk-map",
        "semanticscholar-environment-limited-frequency",
        "environment-limited-threshold",
    } <= resolved_shards


def test_evidence_age_uses_utc_date() -> None:
    text = _read("scripts/docs/checks/check_drift.py")
    assert "datetime.now(UTC).date()" in text
    assert "date.today()" not in text
