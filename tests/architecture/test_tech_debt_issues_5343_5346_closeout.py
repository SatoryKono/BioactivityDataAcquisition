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
"""Closeout evidence guards for tech-debt issues #5343-#5346."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT_PATH = (
    ROOT / "reports" / "quality" / "tech-debt-issues-5343-5346-closeout.json"
)
SCORECARD_PATH = ROOT / "configs" / "quality" / "debt_scorecard.yaml"
EXPECTED_ISSUES = {"#5343", "#5344", "#5345", "#5346"}


def _load_closeout() -> dict[str, Any]:
    payload = json.loads(CLOSEOUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _evidence_path(raw_evidence: str) -> str:
    return raw_evidence.split("::", maxsplit=1)[0]


def test_tech_debt_issues_5343_5346_closeout_covers_exact_issue_set() -> None:
    closeout = _load_closeout()
    issues = cast(list[dict[str, Any]], closeout["issues"])

    assert closeout["status"] == "implemented_local_closeable"
    assert closeout["budget_policy"] == "no_growth_ratchet_only"
    assert {str(issue["issue"]) for issue in issues} == EXPECTED_ISSUES


def test_tech_debt_issues_5343_5346_closeout_evidence_paths_exist() -> None:
    closeout = _load_closeout()
    issues = cast(list[dict[str, Any]], closeout["issues"])
    missing: list[str] = []

    for issue in issues:
        for raw_evidence in cast(list[str], issue["evidence"]):
            relative_path = _evidence_path(raw_evidence)
            if not (ROOT / relative_path).exists():
                missing.append(f"{issue['issue']}: {raw_evidence}")

    assert not missing, "Closeout evidence references missing files:\n" + "\n".join(
        missing
    )


def test_runtime_builder_removed_support_modules_do_not_return() -> None:
    scorecard = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    coverage = cast(
        dict[str, Any],
        cast(dict[str, Any], scorecard["hotspot_family_coverage_thresholds"])[
            "families"
        ],
    )
    runtime_builders = cast(dict[str, Any], coverage["composition_runtime_builders"])
    allowlisted = cast(list[str], runtime_builders["allowlisted_unmeasured_paths"])

    deleted_paths = {
        "src/bioetl/composition/runtime_builders/_run_manifest_creation_support_policy.py",
        "src/bioetl/composition/runtime_builders/_run_manifest_create_spec_support.py",
    }
    assert deleted_paths.isdisjoint(set(allowlisted))
    for relative_path in deleted_paths:
        assert not (ROOT / relative_path).exists(), relative_path


def test_date_only_inventory_burn_down_is_bounded_to_remaining_reviewed_surfaces() -> (
    None
):
    policy = yaml.safe_load(
        (ROOT / "configs" / "quality" / "determinism_identity_policy.yaml").read_text(
            encoding="utf-8"
        )
    )
    hash_policy = cast(dict[str, Any], policy["content_hash_datetime_policy"])
    inventory = cast(list[dict[str, Any]], hash_policy["date_only_entity_inventory"])

    assert len(inventory) == 0
    migrated = {
        ("crossref", "publication"),
        ("openalex", "publication"),
        ("semanticscholar", "publication"),
        ("uniprot", "idmapping"),
    }
    assert migrated.isdisjoint(
        {(str(item["provider"]), str(item["entity"])) for item in inventory}
    )
