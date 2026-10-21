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
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from scripts.engineering.repo import check_scripts_inventory as inventory

pytestmark = pytest.mark.unit


def test_review_expiry_reports_all_decisions_at_fixed_boundary() -> None:
    entries = {
        "scripts/old.py": {"review_by": "2026-10-20", "decision": "shared_helper_module"},
        "scripts/temp.py": {"review_by": "2026-10-20", "decision": "temporary_diagnostic"},
        "scripts/today.py": {"review_by": "2026-10-21"},
        "scripts/future.py": {"review_by": "2026-10-22"},
        "scripts/missing.py": {},
        "scripts/invalid.py": {"review_by": "2026-02-30"},
        "scripts/noncanonical.py": {"review_by": "20261020"},
    }
    report = inventory.build_review_expiry_report(
        {"entries": entries}, today=date(2026, 10, 21)
    )
    assert report["expired_review_by_count"] == 2
    assert report["total_entries"] == 7
    assert report["expired_by_decision"] == {
        "shared_helper_module": 1, "temporary_diagnostic": 1,
    }
    assert [row["path"] for row in report["expired_entries"]] == [
        "scripts/old.py", "scripts/temp.py",
    ]
    assert report["missing_review_by"] == ["scripts/missing.py"]
    assert report["invalid_review_by"] == ["scripts/invalid.py", "scripts/noncanonical.py"]


def test_review_expiry_cli_reports_nonzero_debt_without_failure(
    tmp_path, monkeypatch, capsys,
) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"entries": {
        "scripts/old.py": {"review_by": "2000-01-01", "decision": "shared_helper_module"},
    }}), encoding="utf-8")
    monkeypatch.setattr(inventory, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(inventory, "datetime", SimpleNamespace(
        now=lambda tz: datetime(2026, 10, 21, tzinfo=UTC),
    ))
    monkeypatch.setattr(inventory, "_build_inventory", lambda root: pytest.fail("Unneeded scan"))
    assert inventory.main([
        "--review-expiry", "report", "--lifecycle-registry", "registry.json",
    ]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["expired_review_by_count"] == 1
    assert report["expired_entries"][0]["path"] == "scripts/old.py"


def test_review_expiry_rejects_missing_registry_entries() -> None:
    with pytest.raises(ValueError, match="entries must be a mapping"):
        inventory.build_review_expiry_report({})


def test_load_json_rejects_duplicate_object_keys(tmp_path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        """{
  "entries": {
    "scripts/example.py": {},
    "scripts/example.py": {}
  }
}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="line 3, column 5.*line 4, column 5"):
        inventory._load_json(registry_path)


def test_load_json_accepts_unique_object_keys(tmp_path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps({"entries": {"scripts/example.py": {"owner": "team"}}}),
        encoding="utf-8",
    )

    assert inventory._load_json(registry_path) == {
        "entries": {"scripts/example.py": {"owner": "team"}}
    }


def test_temporary_diagnostic_decision_overrides_strong_reference_groups() -> None:
    refs = [
        inventory.RefEvidence(
            path="scripts/temp/README.md",
            line=1,
            text="report_example.py",
            source_group="scripts",
        )
    ]

    status = inventory._status_for(
        "scripts/temp/report_example.py",
        refs,
        {"scripts/temp/report_example.py": "temporary_diagnostic"},
    )

    assert status == "temporary_diagnostic"


def test_validate_target_registry_entries_rejects_supporting_status_without_taxonomy() -> (
    None
):
    script_map = {
        "scripts/example_supporting.py": {
            "path": "scripts/example_supporting.py",
            "status": "supporting",
        }
    }
    entries_raw = {
        "scripts/example_supporting.py": {
            "owner": "@bioetl-platform",
            "decision": "temporary_diagnostic",
            "review_by": "2026-07-15",
            "next_step": "remove after temporary investigation",
        }
    }

    missing, invalid, forbidden = inventory._validate_target_registry_entries(
        script_map=script_map,
        entries_raw=entries_raw,
        target_statuses=set(inventory.NON_ACTIVE_STATUSES),
        forbid_evaluate_active=True,
    )

    assert missing == []
    assert forbidden == []
    assert invalid == [
        "scripts/example_supporting.py: supporting status requires decision in "
        f"{sorted(inventory.SUPPORTING_LIFECYCLE_DECISIONS)}"
    ]


def test_validate_target_registry_entries_rejects_temporary_diagnostic_status_without_matching_decision() -> (
    None
):
    script_map = {
        "scripts/example_diag.py": {
            "path": "scripts/example_diag.py",
            "status": "temporary_diagnostic",
        }
    }
    entries_raw = {
        "scripts/example_diag.py": {
            "owner": "@bioetl-platform",
            "decision": "shared_helper_module",
            "review_by": "2026-07-15",
            "next_step": "retain as helper",
        }
    }

    missing, invalid, forbidden = inventory._validate_target_registry_entries(
        script_map=script_map,
        entries_raw=entries_raw,
        target_statuses=set(inventory.NON_ACTIVE_STATUSES),
        forbid_evaluate_active=True,
    )

    assert missing == []
    assert forbidden == []
    assert invalid == [
        "scripts/example_diag.py: temporary_diagnostic status requires "
        "decision=temporary_diagnostic"
    ]


def test_validate_stale_registry_entries_rejects_registry_entry_for_active_script() -> (
    None
):
    script_map = {
        "scripts/example_active.py": {
            "path": "scripts/example_active.py",
            "status": "active",
        }
    }
    entries_raw = {
        "scripts/example_active.py": {
            "owner": "@bioetl-platform",
            "decision": "shared_helper_module",
            "review_by": "2026-07-15",
            "next_step": "should have been retired when promoted to active",
        }
    }

    stale, invalid = inventory._validate_stale_registry_entries(
        script_map=script_map,
        entries_raw=entries_raw,
        target_statuses=set(inventory.NON_ACTIVE_STATUSES),
    )

    assert invalid == []
    assert stale == ["scripts/example_active.py: status changed to active"]


@pytest.mark.parametrize(
    "line, expected",
    [
        ("python -m scripts.engineering.repo --help", True),
        ("uv run python -m scripts.diagrams --help", True),
        ("documentation: use -m scripts.engineering.repo as an example", False),
        ("a flag named --mode=-m scripts.engineering.repo", False),
    ],
)
def test_module_reference_detection_requires_command_context(
    line: str, expected: bool
) -> None:
    assert (inventory.MODULE_REF_CANDIDATE_PATTERN.search(line) is not None) is expected
