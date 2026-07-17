"""Tests for deterministic flaky-test burndown review generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.qa.report_flaky_test_burndown_review import (
    build_payload,
    main,
)


def _write_inputs(
    repo_root: Path,
    *,
    entries: list[dict[str, Any]] | None = None,
) -> None:
    inventory = {
        "schema_version": 1,
        "reviewed_on": "2026-07-17",
        "linked_issues": [6351, 5514],
        "evidence_scope": "Curated review bound to static test evidence.",
        "flaky_test_definition": ["intermittent pass/fail outcome"],
        "remediation_workflow": ["stabilize the deterministic seam"],
        "dimensions": {
            "layers": ["application", "domain"],
            "categories": ["Data", "State"],
            "severities": ["P1", "P2"],
            "triage_statuses": ["fixed", "needs-triage"],
            "alert_levels": ["critical", "warning"],
        },
        "reviewed_flaky_tests": entries or [],
        "review_notes": ["Review note."],
    }
    governance = {
        "source_tree_sha256": "a" * 64,
        "budget_violations": [],
        "report": {
            "total_test_functions": 7,
            "total_test_files": 2,
        },
    }
    inventory_path = repo_root / "configs" / "quality" / "flaky_test_inventory.yaml"
    governance_path = repo_root / "reports" / "quality" / "test-governance-current.json"
    inventory_path.parent.mkdir(parents=True)
    governance_path.parent.mkdir(parents=True)
    inventory_path.write_text(
        yaml.safe_dump(inventory, sort_keys=False),
        encoding="utf-8",
    )
    governance_path.write_text(json.dumps(governance), encoding="utf-8")


def _entry(
    nodeid: str,
    *,
    layer: str,
    category: str,
    severity: str,
    triage_status: str,
    alert_level: str,
) -> dict[str, str]:
    return {
        "nodeid": nodeid,
        "owner": "quality-team",
        "cause": "deterministic test cause",
        "remediation": "replace the unstable seam",
        "layer": layer,
        "category": category,
        "severity": severity,
        "triage_status": triage_status,
        "alert_level": alert_level,
    }


def test_build_payload__unsorted_entries__renders_stable_counts_and_order(
    tmp_path: Path,
) -> None:
    _write_inputs(
        tmp_path,
        entries=[
            _entry(
                "tests/unit/test_z.py::test_z",
                layer="domain",
                category="State",
                severity="P2",
                triage_status="needs-triage",
                alert_level="warning",
            ),
            _entry(
                "tests/unit/test_a.py::test_a",
                layer="application",
                category="Data",
                severity="P1",
                triage_status="fixed",
                alert_level="critical",
            ),
        ],
    )

    payload = build_payload(tmp_path)

    assert [row["nodeid"] for row in payload["reviewed_flaky_tests"]] == [
        "tests/unit/test_a.py::test_a",
        "tests/unit/test_z.py::test_z",
    ]
    assert payload["summary"]["total_flaky"] == 2
    assert payload["summary"]["by_layer"] == {"application": 1, "domain": 1}
    assert payload["summary"]["by_triage"] == {
        "fixed": 1,
        "needs-triage": 1,
    }
    assert payload["summary"]["total_tests_analyzed"] == 7
    assert payload["decision"] == "remediation_required"


def test_build_payload__duplicate_nodeid__fails_closed(tmp_path: Path) -> None:
    duplicate = _entry(
        "tests/unit/test_dup.py::test_dup",
        layer="domain",
        category="State",
        severity="P2",
        triage_status="needs-triage",
        alert_level="warning",
    )
    _write_inputs(tmp_path, entries=[duplicate, duplicate])

    with pytest.raises(ValueError, match="Duplicate nodeid"):
        build_payload(tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("reviewed_on", "17 July 2026", "Expected ISO date"),
        ("linked_issues", [5514, 5514], "Duplicate values"),
    ],
)
def test_build_payload__invalid_inventory_metadata__fails_closed(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    _write_inputs(tmp_path)
    inventory_path = tmp_path / "configs" / "quality" / "flaky_test_inventory.yaml"
    inventory = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
    assert isinstance(inventory, dict)
    inventory[field] = value
    inventory_path.write_text(
        yaml.safe_dump(inventory, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=message):
        build_payload(tmp_path)


def test_main__tracked_artifact_lifecycle__detects_missing_current_and_stale(
    tmp_path: Path,
) -> None:
    _write_inputs(tmp_path)
    check_args = ["--repo-root", str(tmp_path), "--check"]

    assert main(check_args) == 1
    assert main(["--repo-root", str(tmp_path)]) == 0
    assert main(check_args) == 0

    output = tmp_path / "reports" / "quality" / "flaky-test-burndown-review.json"
    output.write_text("{}\n", encoding="utf-8")
    assert main(check_args) == 1


def test_main__missing_canonical_input__returns_input_error(tmp_path: Path) -> None:
    assert main(["--repo-root", str(tmp_path)]) == 2
