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

import pytest

from scripts.engineering.repo import check_scripts_inventory as inventory

pytestmark = pytest.mark.unit


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
