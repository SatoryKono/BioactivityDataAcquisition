"""Bounded security and resource-review impact routes retain exact owners."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import (
    affected_pytest_targets,
    build_shadow_compare,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "audit", ["003", "003_extraction", "004", "004_tip", "005", "006", "007"]
)
def test_security_inventory_reviews_route_to_source_qualification_tests(audit):
    root = Path(__file__).resolve().parents[5]
    path = (
        f"configs/quality/external_resource_inventory_security_aud{audit}_review.json"
    )
    report = build_shadow_compare([path], repo_root=root)
    assert (
        "tests/architecture/test_external_resource_inventory_catalog.py"
        in json.dumps(report)
    )
    assert (
        "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py"
        in json.dumps(report)
    )


@pytest.mark.parametrize(
    "review",
    [
        "configs/quality/external_resource_inventory_pr13168_review.json",
        "configs/quality/external_resource_inventory_pr13166_legacy_receipt_review.json",
    ],
)
def test_resource_review_keeps_bounded_source_qualification_routes(review: str) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [review],
        repo_root=root,
    )
    assert {
        "tests/architecture/test_external_resource_inventory_catalog.py",
        "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
    } <= set(report["selected"])
    assert report["covers_full_suite"] is False
    assert report["activation"] == "not_applied"
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare(
            ["configs/quality/external_resource_inventory_pr13168_unreviewed.json"],
            repo_root=root,
        )


def test_hook_qualification_inputs_have_bounded_shadow_routes() -> None:
    root = Path(__file__).resolve().parents[5]
    expected = {
        ".gitattributes": {
            "tests/unit/scripts/repo/test_hook_receipts.py",
            "tests/architecture/test_config_discrepancy_report_drift.py",
            "tests/architecture/test_tech_debt_issues_5847_5852_closeout.py",
        },
        "configs/quality/external_resource_inventory_pr13133_platform_narrowing_review.json": {
            "tests/architecture/test_external_resource_inventory_catalog.py",
            "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
        },
        "configs/quality/external_resource_inventory_pr13133_main_66ef9357_review.json": {
            "tests/architecture/test_external_resource_inventory_catalog.py",
            "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
        },
        "configs/quality/external_resource_inventory_pr13133_main_c41cd6_review.json": {
            "tests/architecture/test_external_resource_inventory_catalog.py",
            "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
        },
        "configs/quality/external_resource_inventory_pr13133_accepted_main_review.json": {
            "tests/architecture/test_external_resource_inventory_catalog.py",
            "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
        },
    }
    for path, owning_tests in expected.items():
        report = build_shadow_compare([path], repo_root=root)
        assert owning_tests <= set(report["selected"]), path
        assert report["covers_full_suite"] is False
    for unknown in (
        ".gitattributes.unreviewed",
        "configs/quality/external_resource_inventory_pr99999_unreviewed_review.json",
        "configs/quality/external_resource_inventory_pr13133_main_unreviewed_review.json",
    ):
        with pytest.raises(ValueError, match="unmapped paths"):
            build_shadow_compare([unknown], repo_root=root)


def test_branch_hygiene_runbook_routes_only_to_owned_checks():
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["docs/05-operations/runbooks/branch-hygiene-wave.md"], repo_root=root
    )
    assert "tests/unit/scripts/repo/test_branch_hygiene.py" in json.dumps(report)
    with pytest.raises(ValueError, match="unmapped"):
        build_shadow_compare(
            ["docs/05-operations/runbooks/branch-hygiene-wave-unknown.md"],
            repo_root=root,
        )


@pytest.mark.parametrize(
    "changed",
    [
        ".github/tooling/jscpd/package-lock.json",
        ".github/tooling/jscpd/package.json",
        ".github/tooling/picomatch-backport/BACKPORT.md",
        ".github/tooling/picomatch-backport/picomatch-4.0.8-bioetl.17.tgz",
        ".github/tooling/picomatch-backport/provenance.json",
        ".github/tooling/picomatch-backport/test.cjs",
        "grafana/plugins/bioetl-scenes-app/package-lock.json",
        "grafana/plugins/bioetl-selectorshell-panel/package.json",
    ],
)
def test_security_backport_inputs_select_executable_security_contracts(
    changed: str,
) -> None:
    root = Path(__file__).resolve().parents[5]
    owner = "tests/architecture/test_picomatch_backport.py"
    assert owner in affected_pytest_targets([changed], repo_root=root)
    assert owner in build_shadow_compare([changed], repo_root=root)["selected"]


def test_lifecycle_review_report_has_specific_impact_owners() -> None:
    root = Path(__file__).resolve().parents[5]
    report = "reports/codex/review_py-audit-bot_20261118_1200_review.md"
    owners = {
        "tests/architecture/test_documentation_cleanup_inventory.py",
        "tests/architecture/test_scripts_lifecycle_registry.py",
        "tests/unit/scripts/qa/test_lifecycle_review_output_destinations.py",
    }
    assert owners <= set(affected_pytest_targets([report], repo_root=root))
    assert owners <= set(build_shadow_compare([report], repo_root=root)["selected"])
    with pytest.raises(ValueError, match="unmapped"):
        build_shadow_compare(["reports/codex/unregistered-review.md"], repo_root=root)
